import React from 'react'

// Consistent 15x15 stroke-based SVG icons (Lucide-style)
// Usage: <Icon name="bank" /> or import specific: import { BankIcon } from './Icons'

interface IconProps {
  size?: number
  className?: string
  style?: React.CSSProperties
}

function Svg({ children, size = 15, className, style }: { children: React.ReactNode } & IconProps) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ flexShrink: 0, ...style }}
    >
      {children}
    </svg>
  )
}

// Finance / Accounts
export const BankIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></Svg>
export const CashIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></Svg>
export const FxIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></Svg>
export const CreditIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h2m4 0h6"/></Svg>
export const CreditCardIcon = (p: IconProps) => <Svg {...p}><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/><circle cx="7" cy="15" r="1" fill="currentColor"/></Svg>
export const InvestmentIcon = (p: IconProps) => <Svg {...p}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></Svg>
export const SavingsIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h12"/></Svg>
export const OtherIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></Svg>

// Navigation
export const DashboardIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></Svg>
export const CalendarIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></Svg>
export const TransactionsIcon = (p: IconProps) => <Svg {...p}><path d="M7 16V4m0 0L3 8m4-4 4 4"/><path d="M17 8v12m0 0 4-4m-4 4-4-4"/></Svg>
export const CategoriesIcon = (p: IconProps) => <Svg {...p}><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></Svg>
export const PlannedIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/></Svg>
export const LoansIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h2m4 0h6"/></Svg>
export const AssetsIcon = (p: IconProps) => <Svg {...p}><path d="M3 22V12l9-9 9 9v10"/><path d="M9 22V16h6v6"/></Svg>
export const MarketIcon = (p: IconProps) => <Svg {...p}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></Svg>
export const InstitutionsIcon = (p: IconProps) => <Svg {...p}><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/></Svg>
export const ReportsIcon = (p: IconProps) => <Svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></Svg>
export const DocumentsIcon = (p: IconProps) => <Svg {...p}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></Svg>
export const ImportIcon = (p: IconProps) => <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></Svg>
export const ExportIcon = (p: IconProps) => <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></Svg>
export const LedgerIcon = (p: IconProps) => <Svg {...p}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></Svg>
export const LockIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></Svg>
export const BackupIcon = (p: IconProps) => <Svg {...p}><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></Svg>
export const SettingsIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></Svg>
export const ProfileIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></Svg>
export const SecurityIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1" fill="currentColor"/></Svg>
export const AppearanceIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></Svg>
export const UsersIcon = (p: IconProps) => <Svg {...p}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></Svg>
export const GroupsIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3H8a2 2 0 0 0-2 2v2h12V5a2 2 0 0 0-2-2z"/></Svg>
export const RolesIcon = (p: IconProps) => <Svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></Svg>
export const AuditIcon = (p: IconProps) => <Svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></Svg>
export const DeleteIcon = (p: IconProps) => <Svg {...p}><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6m4-6v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></Svg>
export const LicenseIcon = (p: IconProps) => <Svg {...p}><path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/></Svg>
export const LinkIcon = (p: IconProps) => <Svg {...p}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></Svg>
export const EditIcon = (p: IconProps) => <Svg {...p}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></Svg>
export const CloseIcon = (p: IconProps) => <Svg {...p}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></Svg>
export const PlusIcon = (p: IconProps) => <Svg {...p}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></Svg>
export const ChevronDownIcon = (p: IconProps) => <Svg {...p}><polyline points="6 9 12 15 18 9"/></Svg>
export const ChevronRightIcon = (p: IconProps) => <Svg {...p}><polyline points="9 18 15 12 9 6"/></Svg>
export const CheckIcon = (p: IconProps) => <Svg {...p}><polyline points="20 6 9 17 4 12"/></Svg>
export const AlertIcon = (p: IconProps) => <Svg {...p}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></Svg>
export const InfoIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></Svg>
export const SearchIcon = (p: IconProps) => <Svg {...p}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></Svg>
export const FilterIcon = (p: IconProps) => <Svg {...p}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></Svg>
export const RefreshIcon = (p: IconProps) => <Svg {...p}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></Svg>
export const DownloadIcon = (p: IconProps) => <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></Svg>
export const UploadIcon = (p: IconProps) => <Svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></Svg>
export const NotificationIcon = (p: IconProps) => <Svg {...p}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></Svg>
export const PaymentIcon = (p: IconProps) => <Svg {...p}><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/><path d="M6 15h2"/></Svg>
export const IncomeIcon = (p: IconProps) => <Svg {...p}><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></Svg>
export const ExpenseIcon = (p: IconProps) => <Svg {...p}><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></Svg>
export const TransferIcon = (p: IconProps) => <Svg {...p}><path d="M7 16V4m0 0L3 8m4-4 4 4"/><path d="M17 8v12m0 0 4-4m-4 4-4-4"/></Svg>
export const EyeIcon = (p: IconProps) => <Svg {...p}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></Svg>
export const EyeOffIcon = (p: IconProps) => <Svg {...p}><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></Svg>
export const UnlockIcon = (p: IconProps) => <Svg {...p}><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></Svg>
export const MoonIcon = (p: IconProps) => <Svg {...p}><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></Svg>
export const ZapIcon = (p: IconProps) => <Svg {...p}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></Svg>
export const SyncIcon = (p: IconProps) => <Svg {...p}><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></Svg>

// Asset type icons
export const RealEstateIcon = (p: IconProps) => <Svg {...p}><path d="M3 22V12l9-9 9 9v10"/><path d="M9 22V16h6v6"/></Svg>
export const VehicleIcon = (p: IconProps) => <Svg {...p}><path d="M5 17H3a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v9a2 2 0 0 1-2 2h-1"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/></Svg>
export const EquipmentIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></Svg>
export const FinancialIcon = (p: IconProps) => <Svg {...p}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></Svg>
export const LandIcon = (p: IconProps) => <Svg {...p}><path d="M3 17l4-8 4 5 3-3 4 6H3z"/><path d="M2 20h20"/></Svg>
export const SecurityAssetIcon = (p: IconProps) => <Svg {...p}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></Svg>
export const CryptoIcon = (p: IconProps) => <Svg {...p}><path d="M11.767 19.089c4.924.868 6.14-6.025 1.216-6.894m-1.216 6.894L5.86 18.047m5.908 1.042-.347 1.97m1.563-8.864c4.924.869 6.14-6.025 1.215-6.893m-1.215 6.893-3.94-.694m5.155-6.2L8.29 4.26m5.908 1.042.348-1.97M7.48 20.364l3.126-17.727"/></Svg>
export const CollectibleIcon = (p: IconProps) => <Svg {...p}><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></Svg>

// Institution type icons
export const BrokerageIcon = (p: IconProps) => <Svg {...p}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></Svg>
export const ExchangeIcon = (p: IconProps) => <Svg {...p}><path d="M7 16V4m0 0L3 8m4-4 4 4"/><path d="M17 8v12m0 0 4-4m-4 4-4-4"/></Svg>
export const InsuranceIcon = (p: IconProps) => <Svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></Svg>
export const BuildingIcon = (p: IconProps) => <Svg {...p}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></Svg>

// Type icon map for account types
export const ACCOUNT_TYPE_ICONS: Record<string, React.ReactNode> = {
  BANK:        <BankIcon />,
  CASH:        <CashIcon />,
  FX:          <FxIcon />,
  CREDIT:      <CreditIcon />,
  CREDIT_CARD: <CreditCardIcon />,
  INVESTMENT:  <InvestmentIcon />,
  SAVINGS:     <SavingsIcon />,
  OTHER:       <OtherIcon />,
}

// Asset type icon map
export const ASSET_TYPE_ICONS: Record<string, React.ReactNode> = {
  REAL_ESTATE: <RealEstateIcon />,
  VEHICLE:     <VehicleIcon />,
  EQUIPMENT:   <EquipmentIcon />,
  FINANCIAL:   <FinancialIcon />,
  LAND:        <LandIcon />,
  SECURITY:    <SecurityAssetIcon />,
  CRYPTO:      <CryptoIcon />,
  COLLECTIBLE: <CollectibleIcon />,
  OTHER:       <OtherIcon />,
}

// Institution type icon map
export const INSTITUTION_TYPE_ICONS: Record<string, React.ReactNode> = {
  BANK:      <BankIcon />,
  BROKERAGE: <BrokerageIcon />,
  EXCHANGE:  <ExchangeIcon />,
  INSURANCE: <InsuranceIcon />,
  OTHER:     <BuildingIcon />,
}

// Notification type icon map
export const NOTIFICATION_TYPE_ICONS: Record<string, React.ReactNode> = {
  PAYMENT_DUE:    <CalendarIcon />,
  PAYMENT_OVERDUE: <AlertIcon />,
  LOAN_DUE:       <BankIcon />,
  CARD_DUE:       <CreditCardIcon />,
  BALANCE_LOW:    <PaymentIcon />,
  IMPORT_DONE:    <DownloadIcon />,
  BACKUP_DONE:    <BackupIcon />,
  OCR_READY:      <SearchIcon />,
  PERIOD_LOCKED:  <LockIcon />,
  SYSTEM_UPDATE:  <NotificationIcon />,
  CUSTOM:         <NotificationIcon />,
}
