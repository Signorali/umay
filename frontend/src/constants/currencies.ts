export interface Currency {
  code: string;
  symbol: string;
  name: string;
  trName: string;
}

export const CURRENCIES: Currency[] = [
  { code: 'TRY', symbol: '₺', name: 'Turkish Lira', trName: 'Türk Lirası' },
  { code: 'USD', symbol: '$', name: 'US Dollar', trName: 'ABD Doları' },
  { code: 'EUR', symbol: '€', name: 'Euro', trName: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound', trName: 'İngiliz Sterlini' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', trName: 'İsviçre Frangı' },
  { code: 'BTC', symbol: '₿', name: 'Bitcoin', trName: 'Bitcoin' },
];

export const getCurrencyName = (code: string, locale: string = 'tr') => {
  const c = CURRENCIES.find(x => x.code === code);
  if (!c) return code;
  return locale.startsWith('tr') ? c.trName : c.name;
};

export const getCurrencySymbol = (code: string) => {
  const c = CURRENCIES.find(x => x.code === code);
  return c ? c.symbol : code;
};
