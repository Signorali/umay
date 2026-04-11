from app.models.base import BaseModel, TenantScopedModel

# Phase 1 — Core platform
from app.models.tenant import Tenant
from app.models.group import Group
from app.models.role import Role
from app.models.permission import Permission, RolePermission
from app.models.user import User, UserGroup
from app.models.audit import AuditLog

# Phase 2 — Financial core
from app.models.account import Account, AccountType
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction, TransactionTag, TransactionType, TransactionStatus
from app.models.ledger import LedgerEntry, EntryType
from app.models.planned_payment import PlannedPayment, PlannedPaymentType, PlannedPaymentStatus, RecurrenceRule
from app.models.loan import Loan, LoanInstallment, LoanStatus, InstallmentStatus
from app.models.credit_card import (
    CreditCard, CreditCardPurchase, CreditCardStatement, CreditCardStatementLine,
    CardStatus, StatementStatus, PurchaseStatus, StatementLineType,
)

# Phase 3 — Advanced finance
from app.models.asset import Asset, AssetValuation, AssetType, AssetStatus
from app.models.institution import Institution, CommissionRule, TaxRule, InstitutionType, CommissionBasis, TaxRuleType
from app.models.investment import Portfolio, InvestmentTransaction, PortfolioPosition, InvestmentTransactionType, InstrumentType, MarketPrice
from app.models.market import MarketProvider, PriceSnapshot, WatchlistItem, ProviderType
from app.models.obligation import SymbolObligation, ObligationDirection, ObligationCounterpartyType, ObligationStatus
from app.models.dashboard import DashboardWidget, WidgetType

# Phase 4 — Documents, OCR, Calendar
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.ocr_draft import OcrDraft, OcrDraftStatus
from app.models.calendar_sync import CalendarItem, CalendarSyncLog, CalendarItemType, CalendarSyncStatus
from app.models.calendar_integration import CalendarIntegration

# Phase 5 — Productization
from app.models.demo import DemoSession
from app.models.system_meta import SystemFlag, MaintenanceWindow

# Phase 6 — Notifications
from app.models.notification import Notification, NotificationType, NotificationPriority

# Phase 7 — Permission enforcement
from app.models.delete_request import DeleteRequest, ALLOWED_TARGET_TABLES

# Transaction templates
from app.models.transaction_template import TransactionTemplate
from app.models.cc_purchase_template import CcPurchaseTemplate

# Licensing
from app.models.license import TenantLicense

# Updates
from app.models.update import UpdateLog

__all__ = [
    # Base
    "BaseModel",
    "TenantScopedModel",
    # Phase 1
    "Tenant", "Group", "Role", "Permission", "RolePermission",
    "User", "UserGroup", "AuditLog",
    # Phase 2
    "Account", "AccountType",
    "Category", "CategoryType",
    "Transaction", "TransactionTag", "TransactionType", "TransactionStatus",
    "LedgerEntry", "EntryType",
    "PlannedPayment", "PlannedPaymentType", "PlannedPaymentStatus", "RecurrenceRule",
    "Loan", "LoanInstallment", "LoanStatus", "InstallmentStatus",
    "CreditCard", "CreditCardPurchase", "CreditCardStatement", "CreditCardStatementLine",
    "CardStatus", "StatementStatus", "PurchaseStatus", "StatementLineType",
    # Phase 3
    "Asset", "AssetValuation", "AssetType", "AssetStatus",
    "Institution", "CommissionRule", "TaxRule", "InstitutionType", "CommissionBasis", "TaxRuleType",
    "Portfolio", "InvestmentTransaction", "PortfolioPosition", "InvestmentTransactionType", "InstrumentType", "MarketPrice",
    "MarketProvider", "PriceSnapshot", "WatchlistItem", "ProviderType",
    "DashboardWidget", "WidgetType",
    # Phase 4
    "Document", "DocumentType", "DocumentStatus",
    "OcrDraft", "OcrDraftStatus",
    "CalendarItem", "CalendarSyncLog", "CalendarItemType", "CalendarSyncStatus",
    # Phase 5
    "DemoSession",
    "SystemFlag", "MaintenanceWindow",
    # Phase 6
    "Notification", "NotificationType", "NotificationPriority",
    # Licensing
    "TenantLicense",
    # Updates
    "UpdateLog",
]
