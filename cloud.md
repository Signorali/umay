# cloud.md
# Umay Product Execution Spec
# Purpose: This file defines the complete product intent, architecture boundaries, non-negotiable rules, delivery phases, and execution constraints for the Umay system.
# Audience: AI coding agents, implementation agents, system design agents, and human developers.
# Status: Source of truth for product scope and execution policy.

---

## 1. PRODUCT IDENTITY

**Product name:** Umay  
**Product type:** Modular, installable, licensable, multi-user financial management platform  
**Primary deployment targets:** Linux servers, Windows servers, VPS environments, compatible ARM systems  
**Primary client targets:** Web client and mobile client  
**Primary goal:** Build a production-capable financial platform before visual refinement

Umay is not a simple budget tracker.

Umay must support:
- multi-user access
- modular permissions
- group and tenant aware data isolation
- large-scale data growth
- strict accounting consistency
- backup and restore
- installation wizard
- reset/factory reset capability
- licensing
- demo mode
- future mobile support
- future OCR/photo-based transaction draft creation
- future market data dashboard
- later unified design system

---

## 2. EXECUTION PRIORITY

The delivery order is fixed.

### Priority order
1. Working core system
2. Security and data integrity
3. Installation and operational readiness
4. Modular business logic
5. Backup and restore
6. Licensing and sale-readiness
7. Mobile/API readiness
8. Advanced modules
9. Dashboard and market data
10. Final unified UI/UX polish

### Rule
Do not optimize visuals before the core is stable.

### Rule
Do not add new major modules before the current phase is complete and verified.

### Rule
No phase closes without health checks, integrity checks, and regression review.

---

## 3. NON-NEGOTIABLE SYSTEM RULES

These rules cannot be broken.

1. All business writes must go through service layer
2. No SQL in route/controller layer
3. Route/API -> Service -> Repo -> DB only
4. Every financial transaction must create ledger records
5. Ledger must always be balanced
6. No direct UI-to-DB write path
7. No silent data mutation without auditability
8. No critical update without backup
9. No phase closure without health checks
10. No AI-generated financial posting without human confirmation
11. No delete behavior that breaks accounting history
12. No architecture shortcuts that weaken future mobile/API compatibility
13. No critical finance flow may create half-written data
14. Mobile and web must use the same business rules
15. Backend authorization is mandatory even if frontend hides actions

---

## 4. SYSTEM CHARACTER

Umay must be designed as:

- platform independent
- container deployable
- API-first
- modular
- secure by default
- audit-friendly
- licensable
- resettable
- backup-aware
- restore-aware
- multi-tenant ready
- mobile-ready
- scalable for high-volume records
- suitable for future productization and resale

---

## 5. ARCHITECTURE MODEL

### Core architecture
- Backend API
- Web application
- Mobile client support layer
- PostgreSQL primary database
- Redis for queue/cache/rate-limit support
- Object/file storage abstraction
- Background worker
- Scheduler
- Reverse proxy
- Audit/logging subsystem
- Backup/restore subsystem
- Licensing subsystem

### Required architecture flow
- API/Route layer receives request
- Service layer validates business rules and permissions
- Repo layer performs database actions
- Ledger service enforces accounting consistency
- Audit service records critical changes
- Background jobs handle heavy non-interactive work

### Database requirement
Primary database must be PostgreSQL.

### Reason
This system is intended for many users and large data volume. SQLite is not the target long-term production database.

---

## 6. DEPLOYMENT MODEL

Umay must be deployable in these modes:

### Mode A - Single machine deployment
- app
- db
- redis
- worker
- reverse proxy

### Mode B - Company/internal server deployment
- same as above
- backup service
- scheduled jobs
- storage management
- monitoring-ready

### Mode C - VPS / production deployment
- app
- db
- redis
- worker
- reverse proxy
- backup service
- object storage abstraction
- monitoring/alarm support

### Packaging requirement
Use container-based deployment logic.

### Compatibility target
- linux/amd64
- linux/arm64

---

## 7. MULTI-TENANT / GROUP-AWARE DATA MODEL

The data model must not assume a single-user system.

Every major record must be designed with isolation-aware ownership, such as:
- tenant_id
- group_id
- user_id

Minimum isolation-aware domains:
- users
- groups
- accounts
- categories
- transactions
- planned payments
- loans
- credit cards
- assets
- investment records
- files/documents
- calendar sync records
- audit records
- license state references
- demo seeds
- OCR/AI draft outputs

---

## 8. CORE MODULES

### 8.1 Users and Permissions
Purpose:
Define who can see, create, edit, delete, approve, or export within each module.

Must support:
- users
- roles
- module permissions
- action permissions
- active/passive state
- role-based access
- user-specific overrides
- permission matrix view
- permission cloning
- audit logging for critical permission changes

Permission actions must at minimum support:
- view
- create
- update
- delete
- approve
- export

### 8.2 Groups
Purpose:
Separate data domains such as company, family, branch, budget set, or ownership group.

Must support:
- group definition
- user-group relation
- group-scoped data access
- group-based reporting

### 8.3 Accounts
Purpose:
Represent every financial location where money, obligations, or investment cash movement exists.

Must support:
- bank accounts
- cash accounts
- FX accounts
- credit/liability accounts
- credit card settlement accounts
- investment accounts
- security accounts
- subaccount hierarchy
- account type
- currency
- opening balance
- institution info
- iban/account identifiers
- active/passive state

### 8.4 Categories
Purpose:
Classify income and expense flows for reporting and accounting alignment.

Must support:
- income categories
- expense categories
- parent/child category structure
- category type
- default ledger/account mapping
- active/passive state
- group-aware category ownership

### 8.5 Transactions
Purpose:
Main financial data entry module.

Must support:
- income entry
- expense entry
- transfer entry
- bulk entry support
- transaction date
- due date
- amount
- currency
- source account
- target account
- category
- description
- tags
- attachments
- notes
- correction flow
- cancellation flow
- reversal flow

Rule:
Every valid financial transaction must produce ledger entries.

### 8.6 Planned Payments
Purpose:
Track future expected income and expense events.

Must support:
- planned income
- planned expense
- recurring plans
- installment plans
- payment date
- due date
- reminder date
- source/target account
- category
- status lifecycle
- calendar reflection

Rule:
A planned payment is not a real transaction until executed or converted.

### 8.7 Loans
Purpose:
Manage borrowed funds, schedule, costs, and closure lifecycle.

Must support:
- lender/institution
- loan purpose
- principal
- net disbursed amount
- fees
- interest
- term
- repayment schedule
- early closure
- restructuring
- repayment history
- remaining liability

### 8.8 Credit Cards
Purpose:
Manage card spending, billing periods, statements, and repayment.

Must support:
- card definition
- bank/institution
- limit
- statement date
- due date
- installment spending
- one-shot spending
- statement generation
- minimum payment
- full payment
- card-linked installments

### 8.9 Assets
Purpose:
Track owned assets such as real estate, vehicles, land, equipment, and similar holdings.

Must support:
- asset type
- purchase date
- purchase value
- current value
- valuation date
- sale details
- gain/loss tracking
- linked documents

### 8.10 Market / Investments
Purpose:
Track investment operations and institution-specific conditions.

Must support:
- brokerage/investment institutions
- institution rules
- commission logic
- tax/withholding rules
- rate/return structures
- instrument types
- buy
- sell
- dividend
- interest income
- cash transfer
- portfolio tracking
- realized/unrealized gain

### 8.11 Institution Settings
Purpose:
Store institution and market operation rules centrally.

Must support:
- banks
- investment institutions
- commission rules
- tax rules
- valuation rules
- dated condition changes

### 8.12 Reporting
Purpose:
Produce meaningful business outputs.

Must support:
- income/expense reports
- account movement reports
- category reports
- group reports
- loan reports
- credit card reports
- asset reports
- investment performance
- cash flow projection

### 8.13 Document Management
Purpose:
Store files linked to financial operations.

Must support:
- receipt
- invoice
- voucher
- contract
- photo
- transaction linking
- secure file storage abstraction
- OCR-ready structure

### 8.14 Calendar Sync
Purpose:
Reflect reminders and due items into personal calendar systems.

Must support:
- planned payment reminders
- loan installment reminders
- credit card due reminders
- collection reminders
- sync logs

Rule:
Application data is the source of truth. Calendar is only a reflection layer.

### 8.15 Backup / Restore
Purpose:
Protect business continuity and support safe recovery.

Must support:
- full backup
- incremental backup
- restore verification
- encrypted backup
- checksum validation
- restore logs
- staging verification

### 8.16 Audit
Purpose:
Record who changed what, where, and when.

Must support:
- actor
- action
- target module
- record identifier
- before/after state reference
- timestamp
- context metadata
- security-sensitive event logging

### 8.17 AI / OCR Assist Layer
Purpose:
Accelerate user work without making autonomous accounting decisions.

Must support:
- OCR extraction from receipt/invoice photos
- category suggestion
- description suggestion
- recurring transaction suggestion
- anomaly hints

Rule:
AI can only create drafts or suggestions. Never final accounting entries without confirmation.

### 8.18 Ledger / Accounting Engine
Purpose:
Guarantee balanced accounting integrity across financial operations.

Must enforce:
- double-entry style posting
- debit/credit balance
- unique posting source linkage
- orphan prevention
- duplicate prevention
- integrity verification

---

## 9. MARKET DATA SUBSYSTEM

This is a dedicated subsystem, not just a small screen.

### Required capabilities
- FX rates
- stock prices
- commodity prices
- interest/rate indicators
- index values
- selected symbol watchlists
- latest price snapshot
- historical snapshots
- provider source tracking
- delayed/realtime label
- last update timestamp
- user-selected watchlist
- group-shared watchlist support
- polling worker
- cache layer
- manual override support for admin workflows

### Provider design rule
Do not hardcode a single market provider.

Use provider abstraction:
- market provider interface
- pluggable provider implementations
- fallback-capable structure
- provider logging
- source-aware price records

### Dashboard relation
Selected market symbols must be visible in dashboard summaries.

---

## 10. DASHBOARD MODEL

Dashboard is not final visual polish yet.  
Dashboard is a configurable summary layer.

### Must support
- selected year
- selected period
- configurable widgets
- selected market indicators
- account summary
- planned payment summary
- loan summary
- card due summary
- portfolio total
- favorite symbols
- latest activities

### Rule
Dashboard data model must be built now even if advanced charts are implemented later.

---

## 11. INSTALLATION WIZARD

System must not start directly into production mode on first boot.

### First-run installation flow
1. environment pre-check
2. license state check
3. database readiness check
4. migration execution
5. first admin creation
6. tenant/group bootstrap
7. base currency/system settings
8. security secrets initialization
9. optional demo data setup
10. activation of normal operation

### Pre-check minimums
- writable storage
- backup path readiness
- database connectivity
- time/sync sanity
- environment config validity
- port availability
- required secret presence

---

## 12. RESET / FACTORY RESET

The system must support controlled reset operations.

### Reset modes
- clear demo data
- clear operational financial data
- factory reset

### Mandatory safety
- highest privilege only
- master confirmation
- second confirmation step
- audit entry
- recommended pre-reset backup
- maintenance mode support

---

## 13. LICENSING

The product must be sale-ready and licensable.

### Licensing must support
- trial license
- time-limited license
- permanent license
- module-based license
- user-count limits
- tenant/group limits
- machine/server binding if required
- offline validation option
- renewal support
- suspended/expired states

### Design rule
License logic must be a dedicated subsystem.
Do not scatter fragile frontend-only license checks across the system.

---

## 14. SECURITY REQUIREMENTS

Security is not optional.

### Minimum security expectations
- TLS/HTTPS-ready deployment
- secure password hashing
- rate limiting
- brute force protection
- session/device management
- secure secret handling
- encrypted backup storage
- file upload validation
- role/permission enforcement at backend
- suspicious access awareness
- support for MFA later
- protection of license and secret data

### Data protection model
Use layered protection:
- transport protection
- storage protection
- secret protection
- backup protection
- audit protection

---

## 15. DATA INTEGRITY RULES

### Mandatory rules
- every critical financial action is atomic
- use DB transaction boundaries
- rollback on failure
- never allow half-written ledger-linked data
- destructive operations must not break auditability

### Reversal rule
For accounting-sensitive records, prefer reversal/counter-entry logic over destructive deletion.

### Delete rule
Differentiate:
- soft delete
- protected records
- privileged hard delete only where safe

---

## 16. PERIOD LOCKING

Historical periods must not remain freely mutable.

### Must support
- month close
- period lock
- restricted edits in locked period
- privileged reopen flow
- audit trail for lock state changes

---

## 17. MULTI-CURRENCY

Required at architecture level.

### Must support
- account currency
- transaction currency
- base/reporting currency
- exchange rates
- manual rate entry
- later external rate integration
- historical rate awareness
- FX difference-ready design

---

## 18. CONCURRENCY AND IDEMPOTENCY

### Concurrency
Protect against conflicting edits.

Use one of:
- optimistic locking
- versioning
- targeted row locking where needed

### Idempotency
Prevent duplicate execution for create/update/payment-sensitive API requests.

Mandatory for:
- mobile-originated financial writes
- unstable network retries
- critical create actions

---

## 19. API DESIGN

### Rules
- API-first
- web and mobile share backend business logic
- versioned endpoints
- consistent validation
- consistent error contract
- authorization enforced server-side

### Goal
No duplicate business logic branches for mobile vs web.

---

## 20. BACKGROUND JOBS

Heavy operations must not block primary request flow.

### Worker-eligible jobs
- backup creation
- restore preparation
- OCR processing
- AI suggestion generation
- market polling
- calendar sync
- import processing
- heavy report generation
- cleanup jobs
- alerts/notifications

---

## 21. NOTIFICATIONS AND ALERTS

Must support a notification foundation.

### Notification types
- in-app
- email
- mobile push-ready architecture later

### Alert examples
- backup failure
- disk risk
- license expiry
- provider failure
- suspicious login
- high error rate

---

## 22. IMPORT / EXPORT

Must be first-class, not an afterthought.

### Import support
- CSV
- spreadsheet import
- bank statement import
- controlled field mapping
- validation report
- partial failure reporting

### Export support
- report export
- data export
- support diagnostics package
- owner-controlled data portability

---

## 23. OBSERVABILITY AND HEALTH

Must provide operational visibility.

### Log domains
- application logs
- audit logs
- worker logs
- sync logs
- backup logs
- restore logs
- OCR/AI logs
- market provider logs
- security event logs

### Health summary must eventually support
- ledger integrity state
- backup status
- queue status
- sync failures
- provider state
- license state
- DB health indicators

---

## 24. UPDATE AND MAINTENANCE MODEL

### Must support
- versioned releases
- migration-managed updates
- pre-update backup
- post-update health verification
- maintenance mode
- rollback planning for failed updates

---

## 25. DEMO MODE

A limited demo data mode must exist once the core system is fully working.

### Demo dataset target
- around 5 sample records per key module
- isolated from real business data
- removable safely
- useful for product demonstrations and onboarding

---

## 26. UI/UX STRATEGY

Do not fully polish visuals before the core is stable.

### Current UI goal
- functional
- consistent skeleton
- reusable layouts
- reusable forms
- reusable table patterns
- reusable action areas

### Final UI goal
All screens must eventually share:
- same structure
- same spacing logic
- same color system
- same component language
- same interaction rhythm

User must not feel that different modules belong to different products.

---

## 27. PHASED DELIVERY PLAN

### Phase 1 - Core platform
- tenant/group base
- users
- permissions
- license core
- installation wizard
- reset/factory reset infrastructure
- audit base
- security base
- backup base

### Phase 2 - Financial core
- accounts
- categories
- transactions
- ledger engine
- planned payments
- loans
- credit cards

### Phase 3 - Advanced finance
- assets
- investments
- institution settings
- reporting base
- market data subsystem
- dashboard data model

### Phase 4 - Mobile and document workflows
- document system
- file/photo upload
- OCR draft flow
- calendar sync
- mobile/API hardening

### Phase 5 - Productization
- demo mode
- licensing scenarios
- update/maintenance flow
- restore validation
- export/diagnostics packages

### Phase 6 - Final unified UI
- design system application
- consistent screens
- advanced dashboard
- charts
- full visual standardization

---

## 28. DELIVERY GATES

A phase is not complete unless:
- critical health checks pass
- integrity checks pass
- backup rule for that phase exists
- regression risk is reviewed
- no major architecture rule was violated

---

## 29. STRICTLY FORBIDDEN

- SQL in route/controller layer
- direct UI-to-DB mutation
- ledger bypass
- silent accounting edits
- AI autonomous accounting posting
- destructive changes without recovery logic
- new major module before current phase stability
- frontend-only security assumptions
- provider hard-dependency for market data
- visually polishing broken business logic

---

## 30. FINAL PRODUCT STATEMENT

Umay must become:

- installable
- licensable
- secure
- modular
- audit-friendly
- mobile-ready
- web-ready
- backup-aware
- restore-aware
- accounting-safe
- market-data-capable
- dashboard-capable
- productized for resale
- later unified by a single design language

### Final rule
Build the working and trustworthy core first.
Apply final visual perfection last.
