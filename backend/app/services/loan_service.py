"""Loan service — loan and installment lifecycle management."""
import uuid
import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from dateutil.relativedelta import relativedelta

from app.models.loan import Loan, LoanInstallment, LoanStatus, InstallmentStatus
from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionTag
from app.models.planned_payment import PlannedPayment, PlannedPaymentType, PlannedPaymentStatus
from app.models.ledger import LedgerEntry
from app.repositories.loan import LoanRepository, LoanInstallmentRepository
from app.repositories.account import AccountRepository
from app.schemas.loan import LoanCreate, LoanUpdate, InstallmentPayRequest, EarlyCloseRequest
from app.schemas.transaction import TransactionCreate
from app.services.audit_service import AuditService
from app.services.transaction_service import TransactionService
from app.core.exceptions import NotFoundError, BusinessRuleError


class LoanService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LoanRepository(session)
        self.installment_repo = LoanInstallmentRepository(session)
        self.audit = AuditService(session)
        self.tx_service = TransactionService(session)
        self.acct_repo = AccountRepository(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: LoanCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Loan:
        """
        Kredi oluşturma mantığı:
        1. Toplam Geri Ödeme (Taksitler) = Taksit Sayısı × Taksit Tutarı
        2. Toplam Yükümlülük = Toplam Geri Ödeme + Masraf
        3. Borç Hesabı Açılış Bakiyesi = - (Toplam Yükümlülük)
        4. Masraf İşlemi: Kredi hesabına GELİR (+) olarak kaydedilir. 
           Böylece kredi hesabının bakiyesi -(Taksitler Toplamı) olur.
        5. Kullandırım İşlemi: Net tutar hedef banka hesabına GELİR olarak geçer.
        """
        maturity_date = data.start_date + relativedelta(months=data.term_months)

        # Taksitlerin toplamı
        installments_total = data.term_months * data.installment_amount
        # Toplam maliyet (Taksitler + Masraf)
        total_loan_cost = installments_total + data.fees
        
        # 1. Borç hesabı açılışı (Negatif toplam maliyet: Örn: -146.000)
        # Bu rakam kredi yükümlülüğünün tamamını temsil eder.
        initial_liability = Decimal("0") - total_loan_cost

        liability_account = Account(
            tenant_id=tenant_id,
            group_id=data.group_id,
            name=f"Kredi Borç: {data.lender_name}",
            account_type=AccountType.CREDIT,
            currency=data.currency,
            opening_balance=initial_liability,
            current_balance=initial_liability,
            description=f"Kredi borç hesabı: {data.loan_purpose or data.lender_name}"
        )
        liability_account = await self.acct_repo.create(liability_account)
        await self.session.flush()

        # 2. Net kullanılan tutarı banka hesabına GELİR olarak işle
        await self.tx_service.create(
            tenant_id=tenant_id,
            group_id=data.group_id,
            data=TransactionCreate(
                transaction_type=TransactionType.INCOME,
                status=TransactionStatus.CONFIRMED,
                amount=data.disbursed_amount,
                currency=data.currency,
                target_account_id=data.target_account_id,
                transaction_date=data.start_date,
                description=f"Kredi Kullanımı (Net): {data.lender_name} - {data.loan_purpose or ''}",
                system_generated=True,
            ),
            actor_id=actor_id, actor_email=actor_email, force=True
        )

        # 3. Masrafı Krediye pozitif ödeme (+) olarak işle 
        # Bu işlem borç hesabına bir GELİR (Income) girişi yaparak bakiyeyi masraf kadar düzeltir.
        # Örn: -146.000 + 2.000 = -144.000 (Gerçek borç)
        if data.fees > 0:
            await self.tx_service.create(
                tenant_id=tenant_id,
                group_id=data.group_id,
                data=TransactionCreate(
                    transaction_type=TransactionType.INCOME,
                    status=TransactionStatus.CONFIRMED,
                    amount=data.fees,
                    currency=data.currency,
                    target_account_id=liability_account.id,
                    transaction_date=data.start_date,
                    description=f"Kredi Masraf Ödemesi (Açılış): {data.lender_name}",
                    system_generated=True,
                ),
                actor_id=actor_id, actor_email=actor_email, force=True
            )

        # 4. Kredi Kaydı
        # Kalan borç = Taksitlerin toplamı
        loan = Loan(
            tenant_id=tenant_id,
            group_id=data.group_id,
            lender_name=data.lender_name,
            loan_purpose=data.loan_purpose,
            principal=data.principal,
            disbursed_amount=data.disbursed_amount,
            fees=data.fees,
            currency=data.currency,
            term_months=data.term_months,
            payment_day=data.payment_day,
            installment_amount=data.installment_amount,
            start_date=data.start_date,
            maturity_date=maturity_date,
            remaining_balance=installments_total,
            total_paid=data.fees, # Masraf baştan ödendi sayılır
            account_id=liability_account.id,
            category_id=data.category_id,
            notes=data.notes,
        )
        loan = await self.repo.create(loan)

        # 5. Taksit Planı
        for i in range(1, data.term_months + 1):
            dt = data.start_date + relativedelta(months=i)
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            p_day = min(data.payment_day, last_day)
            due_date = dt.replace(day=p_day)

            inst = LoanInstallment(
                loan_id=loan.id,
                installment_number=i,
                due_date=due_date,
                principal_amount=data.installment_amount,
                interest_amount=Decimal("0"),
                total_amount=data.installment_amount,
            )
            self.session.add(inst)

            pp = PlannedPayment(
                tenant_id=tenant_id,
                group_id=data.group_id,
                payment_type=PlannedPaymentType.EXPENSE,
                title=f"{data.lender_name} Taksit {i}/{data.term_months}",
                amount=data.installment_amount,
                currency=data.currency,
                account_id=liability_account.id,
                category_id=data.category_id,
                planned_date=due_date,
                due_date=due_date,
                total_installments=data.term_months,
                current_installment=i,
                loan_id=loan.id,
                notes=f"Kredi Taksiti - {loan.loan_purpose or ''}",
            )
            self.session.add(pp)

        await self.session.flush()

        await self.audit.log(
            action="CREATE",
            module="loans",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(loan.id),
        )
        return loan

    async def get_by_id(self, loan_id: uuid.UUID, tenant_id: uuid.UUID) -> Loan:
        loan = await self.repo.get_by_id_and_tenant(loan_id, tenant_id)
        if not loan:
            raise NotFoundError("Loan")
        return loan

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, status: Optional[LoanStatus] = None,
        offset: int = 0, limit: int = 50, group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[Loan], int]:
        return await self.repo.get_by_tenant(tenant_id, status=status, offset=offset, limit=limit,
                                             group_ids=group_ids)

    async def get_installments(self, loan_id: uuid.UUID, tenant_id: uuid.UUID) -> List[LoanInstallment]:
        await self.get_by_id(loan_id, tenant_id)  # verify ownership
        return await self.installment_repo.get_by_loan(loan_id)

    async def pay_installment(
        self,
        loan_id: uuid.UUID,
        installment_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: InstallmentPayRequest,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> LoanInstallment:
        """Record a payment against a specific installment."""
        loan = await self.get_by_id(loan_id, tenant_id)
        if not loan.account_id:
            raise BusinessRuleError("Loan is not linked to a liability account.")

        inst = await self.installment_repo.get_by_id(installment_id)
        if not inst or inst.loan_id != loan_id:
            raise NotFoundError("LoanInstallment")
        if inst.status == InstallmentStatus.PAID:
            raise BusinessRuleError("Installment is already paid")

        pay_date = data.paid_date or datetime.now(timezone.utc).date()
        discount = data.interest_discount or Decimal("0")
        late_fee = data.late_interest or Decimal("0")

        # Actual cash transferred = installment minus any discount
        cash_transfer = data.amount - discount
        if cash_transfer <= Decimal("0"):
            raise BusinessRuleError("Faiz indirimi taksit tutarından büyük olamaz.")

        # Create TRANSFER: source (user account) → target (liability account)
        tx = await self.tx_service.create(
            tenant_id=tenant_id,
            group_id=loan.group_id,
            data=TransactionCreate(
                transaction_type=TransactionType.TRANSFER,
                status=TransactionStatus.CONFIRMED,
                amount=cash_transfer,
                currency=loan.currency,
                source_account_id=data.source_account_id,
                target_account_id=loan.account_id,
                transaction_date=pay_date,
                description=f"{loan.lender_name} Taksit Ödemesi ({inst.installment_number}/{loan.term_months})",
            ),
            actor_id=actor_id, actor_email=actor_email, force=True
        )

        # Faiz indirimi — banka indirimini gelir olarak yükümlülük hesabına yaz
        if discount > Decimal("0"):
            await self.tx_service.create(
                tenant_id=tenant_id,
                group_id=loan.group_id,
                data=TransactionCreate(
                    transaction_type=TransactionType.INCOME,
                    status=TransactionStatus.CONFIRMED,
                    amount=discount,
                    currency=loan.currency,
                    target_account_id=loan.account_id,
                    transaction_date=pay_date,
                    description=f"{loan.lender_name} Faiz İndirimi — Taksit {inst.installment_number}/{loan.term_months}",
                    system_generated=True,
                ),
                actor_id=actor_id, actor_email=actor_email, force=True
            )

        # Gecikme faizi — ayrı gider işlemi olarak kaydet
        if late_fee > Decimal("0"):
            await self.tx_service.create(
                tenant_id=tenant_id,
                group_id=loan.group_id,
                data=TransactionCreate(
                    transaction_type=TransactionType.EXPENSE,
                    status=TransactionStatus.CONFIRMED,
                    amount=late_fee,
                    currency=loan.currency,
                    source_account_id=data.source_account_id,
                    transaction_date=pay_date,
                    category_id=data.late_interest_category_id,
                    description=f"{loan.lender_name} Gecikme Faizi — Taksit {inst.installment_number}/{loan.term_months}",
                    system_generated=True,
                ),
                actor_id=actor_id, actor_email=actor_email, force=True
            )

        new_paid = (inst.paid_amount or Decimal("0")) + data.amount
        if new_paid >= inst.total_amount:
            new_status = InstallmentStatus.PAID
            paid_date = pay_date
        else:
            new_status = InstallmentStatus.PARTIALLY_PAID
            paid_date = inst.paid_date

        inst = await self.installment_repo.update(
            inst,
            paid_amount=new_paid,
            status=new_status,
            paid_date=paid_date,
            linked_transaction_id=tx.id,
        )

        # Update loan totals (full installment amount reduces balance)
        new_total_paid = (loan.total_paid or Decimal("0")) + data.amount
        new_remaining = max(Decimal("0"), (loan.remaining_balance or Decimal("0")) - data.amount)
        update_fields = {"total_paid": new_total_paid, "remaining_balance": new_remaining}

        # Auto-close if fully paid
        if new_remaining <= 0:
            update_fields["status"] = LoanStatus.PAID_OFF

        await self.repo.update(loan, **update_fields)

        # Auto-close matching planned payment
        pp = await self.session.scalar(
            select(PlannedPayment).where(
                PlannedPayment.account_id == loan.account_id,
                PlannedPayment.current_installment == inst.installment_number,
                PlannedPayment.tenant_id == tenant_id,
                PlannedPayment.is_deleted == False
            )
        )
        if pp and pp.status not in (PlannedPaymentStatus.PAID, PlannedPaymentStatus.CANCELLED):
            pp.status = PlannedPaymentStatus.PAID
            pp.paid_amount = pp.amount
            pp.linked_transaction_id = tx.id
            self.session.add(pp)

        await self.audit.log(
            action="PAY_INSTALLMENT",
            module="loans",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(loan_id),
            after={"installment_id": str(installment_id), "amount": str(data.amount)},
        )
        return inst

    async def early_close(
        self,
        loan_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: EarlyCloseRequest,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Loan:
        """
        Early closure of a loan.
        
        Process:
        1. User pays `data.amount` from their account to the liability account
        2. If data.amount < remaining_balance, the difference is treated as
           "interest savings / discount" → recorded as INCOME
        3. Loan balance goes to 0, status → PAID_OFF
        4. All pending installments → PAID, all pending planned payments → PAID
        """
        loan = await self.get_by_id(loan_id, tenant_id)
        if loan.status != LoanStatus.ACTIVE:
            raise BusinessRuleError("Sadece aktif krediler erken kapatılabilir.")
        if not loan.account_id:
            raise BusinessRuleError("Kredi hesabı bulunamadı.")

        remaining = loan.remaining_balance or Decimal("0")
        if remaining <= 0:
            raise BusinessRuleError("Bu kredinin kalan borcu bulunmamaktadır.")

        close_date = data.close_date or datetime.now(timezone.utc).date()
        payment_amount = data.amount
        discount = remaining - payment_amount  # positive = savings

        if payment_amount <= 0:
            raise BusinessRuleError("Ödeme tutarı sıfırdan büyük olmalıdır.")
        if payment_amount > remaining:
            raise BusinessRuleError(
                f"Ödeme tutarı ({payment_amount}) kalan borçtan ({remaining}) büyük olamaz."
            )

        # 1. Transfer: user account → liability account (actual payment)
        await self.tx_service.create(
            tenant_id=tenant_id,
            group_id=loan.group_id,
            data=TransactionCreate(
                transaction_type=TransactionType.TRANSFER,
                status=TransactionStatus.CONFIRMED,
                amount=payment_amount,
                currency=loan.currency,
                source_account_id=data.source_account_id,
                target_account_id=loan.account_id,
                transaction_date=close_date,
                description=f"{loan.lender_name} Erken Kapama Ödemesi",
            ),
            actor_id=actor_id, actor_email=actor_email, force=True
        )

        # 2. If discount > 0, record as income (interest savings)
        if discount > 0:
            await self.tx_service.create(
                tenant_id=tenant_id,
                group_id=loan.group_id,
                data=TransactionCreate(
                    transaction_type=TransactionType.INCOME,
                    status=TransactionStatus.CONFIRMED,
                    amount=discount,
                    currency=loan.currency,
                    target_account_id=loan.account_id,
                    transaction_date=close_date,
                    description=f"{loan.lender_name} Faiz Tasarrufu (Erken Kapama)",
                    system_generated=True,
                ),
                actor_id=actor_id, actor_email=actor_email, force=True
            )

        # 3. Update loan: fully paid off
        new_total_paid = (loan.total_paid or Decimal("0")) + payment_amount
        loan = await self.repo.update(
            loan,
            total_paid=new_total_paid,
            remaining_balance=Decimal("0"),
            status=LoanStatus.PAID_OFF,
        )

        # 4. Close all pending installments
        installments = await self.installment_repo.get_by_loan(loan_id)
        for inst in installments:
            if inst.status in (InstallmentStatus.PENDING, InstallmentStatus.PARTIALLY_PAID, InstallmentStatus.OVERDUE):
                await self.installment_repo.update(
                    inst,
                    status=InstallmentStatus.PAID,
                    paid_date=close_date,
                )

        # 5. Close all pending planned payments
        pp_result = await self.session.execute(
            select(PlannedPayment).where(
                PlannedPayment.account_id == loan.account_id,
                PlannedPayment.tenant_id == tenant_id,
                PlannedPayment.is_deleted == False,
                PlannedPayment.status.in_([
                    PlannedPaymentStatus.PENDING,
                    PlannedPaymentStatus.OVERDUE,
                ])
            )
        )
        for pp in pp_result.scalars().all():
            pp.status = PlannedPaymentStatus.CANCELLED
            self.session.add(pp)

        await self.session.flush()

        await self.audit.log(
            action="EARLY_CLOSE",
            module="loans",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(loan_id),
            after={
                "payment_amount": str(payment_amount),
                "discount": str(discount),
                "close_date": str(close_date),
            },
        )
        return loan

    async def delete_loan(
        self,
        loan_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        """
        Kredi ve bağlı tüm kayıtları siler.
        Sadece taksit ödemesi yapılmamış krediler silinebilir.
        (Oluşturma sırasındaki masraf işlemi kullanıcı ödemesi sayılmaz.)
        """
        loan = await self.get_by_id(loan_id, tenant_id)

        # Kontrol: herhangi bir taksit ödenmiş mi?
        installments = await self.installment_repo.get_by_loan(loan_id)
        has_payment = any(
            inst.status in (InstallmentStatus.PAID, InstallmentStatus.PARTIALLY_PAID)
            for inst in installments
        )
        if has_payment:
            raise BusinessRuleError("Ödeme yapılmış bir kredi silinemez. Önce ödemeleri iptal etmelisiniz.")

        # 1. Borç hesabıyla ilişkili işlemleri bul ve bakiye etkisini geri al
        if loan.account_id:
            tx_results = await self.session.execute(
                select(Transaction).where(
                    (Transaction.source_account_id == loan.account_id) |
                    (Transaction.target_account_id == loan.account_id)
                )
            )
            txs = tx_results.scalars().all()
            for tx in txs:
                # Bakiye etkisini geri al
                amount = tx.amount
                if tx.transaction_type == TransactionType.INCOME and tx.target_account_id:
                    target_acct = await self.session.get(Account, tx.target_account_id)
                    if target_acct:
                        target_acct.current_balance = (target_acct.current_balance or Decimal("0")) - amount
                        self.session.add(target_acct)
                elif tx.transaction_type == TransactionType.EXPENSE and tx.source_account_id:
                    src_acct = await self.session.get(Account, tx.source_account_id)
                    if src_acct:
                        src_acct.current_balance = (src_acct.current_balance or Decimal("0")) + amount
                        self.session.add(src_acct)
                elif tx.transaction_type == TransactionType.TRANSFER:
                    if tx.target_account_id:
                        target_acct = await self.session.get(Account, tx.target_account_id)
                        if target_acct:
                            target_acct.current_balance = (target_acct.current_balance or Decimal("0")) - amount
                            self.session.add(target_acct)
                    if tx.source_account_id:
                        src_acct = await self.session.get(Account, tx.source_account_id)
                        if src_acct:
                            src_acct.current_balance = (src_acct.current_balance or Decimal("0")) + amount
                            self.session.add(src_acct)
                # Ledger girdilerini ve tag'leri sil
                await self.session.execute(
                    delete(LedgerEntry).where(LedgerEntry.transaction_id == tx.id)
                )
                await self.session.execute(
                    delete(TransactionTag).where(TransactionTag.transaction_id == tx.id)
                )
                await self.session.delete(tx)

            # 2. Planlı ödemeleri sil
            await self.session.execute(
                delete(PlannedPayment).where(PlannedPayment.account_id == loan.account_id)
            )

            # 3. Borç hesabını sil
            acct = await self.session.get(Account, loan.account_id)
            if acct:
                await self.session.delete(acct)

        # 4. Kullandırım (disbursed) ve masraf işlemlerini bul ve temizle
        #    Bu işlemler borç hesabı değil, kullanıcının banka/nakit hesabını hedef alır
        extra_tx_result = await self.session.execute(
            select(Transaction).where(
                Transaction.tenant_id == tenant_id,
                Transaction.description.like(f"Kredi Kullanımı%{loan.lender_name}%"),
            )
        )
        extra_tx_result2 = await self.session.execute(
            select(Transaction).where(
                Transaction.tenant_id == tenant_id,
                Transaction.description.like(f"Kredi Masrafı%{loan.lender_name}%"),
            )
        )
        all_extra_txs = list(extra_tx_result.scalars().all()) + list(extra_tx_result2.scalars().all())
        # Deduplicate
        seen_ids = set()
        unique_extra_txs = []
        for tx in all_extra_txs:
            if tx.id not in seen_ids:
                seen_ids.add(tx.id)
                unique_extra_txs.append(tx)
        for ext_tx in unique_extra_txs:
            amount = ext_tx.amount
            # Bakiye etkisini geri al
            if ext_tx.transaction_type == TransactionType.INCOME and ext_tx.target_account_id:
                target_acct = await self.session.get(Account, ext_tx.target_account_id)
                if target_acct:
                    target_acct.current_balance = (target_acct.current_balance or Decimal("0")) - amount
                    self.session.add(target_acct)
            elif ext_tx.transaction_type == TransactionType.EXPENSE and ext_tx.source_account_id:
                src_acct = await self.session.get(Account, ext_tx.source_account_id)
                if src_acct:
                    src_acct.current_balance = (src_acct.current_balance or Decimal("0")) + amount
                    self.session.add(src_acct)
            # Ledger girdilerini ve tag'leri sil
            await self.session.execute(
                delete(LedgerEntry).where(LedgerEntry.transaction_id == ext_tx.id)
            )
            await self.session.execute(
                delete(TransactionTag).where(TransactionTag.transaction_id == ext_tx.id)
            )
            await self.session.delete(ext_tx)

        await self.session.flush()

        # 5. Taksit kayıtlarını sil
        await self.session.execute(
            delete(LoanInstallment).where(LoanInstallment.loan_id == loan.id)
        )

        # 6. Kredi kaydını sil
        await self.session.delete(loan)

        await self.audit.log(
            action="DELETE_FULL",
            module="loans",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(loan_id),
            notes="Kredi ve bağlı tüm hesap/hareketler kalıcı olarak silindi."
        )

    async def close(
        self,
        loan_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Loan:
        """Mark a loan as paid off."""
        loan = await self.get_by_id(loan_id, tenant_id)
        if loan.status != LoanStatus.ACTIVE:
            raise BusinessRuleError(f"Cannot close a loan with status {loan.status}")

        loan = await self.repo.update(loan, status=LoanStatus.PAID_OFF, remaining_balance=Decimal("0"))
        await self.audit.log(
            action="CLOSE",
            module="loans",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(loan_id),
        )
        return loan
