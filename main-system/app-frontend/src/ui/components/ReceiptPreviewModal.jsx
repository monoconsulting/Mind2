import React from 'react';
import { FiX, FiSave, FiEdit2, FiTrash2, FiCreditCard, FiChevronDown, FiChevronLeft, FiChevronRight, FiRefreshCw } from 'react-icons/fi';
import { api } from '../api';

// Helper functions
function normaliseFieldId(value) {
  if (!value || typeof value !== 'string') {
    return '';
  }
  const lower = value.toLowerCase().trim();
  const withoutPrefix = lower.replace(/^(receipt|unified_files|receipt_items|accounting_proposals|items|line_items|proposals)./i, '');
  const withoutBrackets = withoutPrefix.replace(/[\d+]/g, '');
  return withoutBrackets;
}

function resolveBoxField(boxes, candidates) {
  if (!Array.isArray(boxes) || !Array.isArray(candidates)) {
    return candidates[0];
  }
  const normalised = candidates.map((c) => normaliseFieldId(c));
  const match = boxes.find((box) => normalised.includes(normaliseFieldId(box.field)));
  return match?.field || candidates[0];
}

function buildHoverCandidates(key, options = {}) {
  const { source = 'receipt', extras = [], index } = options;
  const candidates = [];

  const isValidIndex = typeof index === 'number' && Number.isFinite(index) && index >= 0;

  // Add index-qualified candidate first so arrays can match distinct overlays.
  if (source && isValidIndex) {
    candidates.push(`${source}[${index}].${key}`);
  }

  // Add primary candidate with source prefix.
  if (source) {
    candidates.push(`${source}.${key}`);
  }

  // Add the key itself as a generic fallback.
  candidates.push(key);

  // Add all extra candidates (supporting optional index-qualified variants).
  if (Array.isArray(extras)) {
    extras.forEach((extra) => {
      if (typeof extra === 'string' && extra.length > 0) {
        candidates.push(extra);
        if (isValidIndex && extra.includes('[]')) {
          candidates.push(extra.replace('[]', `[${index}]`));
        }
      }
    });
  }

  // Deduplicate while preserving order to keep resolveBoxField deterministic.
  return [...new Set(candidates)];
}

function firstNonEmptyArray(source, keys) {
  if (!source || typeof source !== 'object') {
    return [];
  }
  for (const key of keys) {
    const value = source[key];
    if (Array.isArray(value) && value.length > 0) {
      return value;
    }
  }
  const fallbackKey = keys.find((key) => Array.isArray(source[key]));
  if (fallbackKey) {
    return source[fallbackKey];
  }
  return [];
}

async function attachLineItemsFallback(payload, receiptId) {
  if (!receiptId || !payload || typeof payload !== 'object') {
    return payload;
  }
  const existing = firstNonEmptyArray(payload, ['items', 'receipt_items', 'line_items', 'unified_file_items']);
  if (Array.isArray(existing) && existing.length > 0) {
    return payload;
  }
  try {
    const res = await api.fetch(`/ai/api/receipts/${receiptId}/line-items`);
    if (!res.ok) {
      return payload;
    }
    const data = await res.json();
    const fallback = Array.isArray(data?.line_items)
      ? data.line_items
      : Array.isArray(data)
        ? data
        : [];
    if (!fallback.length) {
      return payload;
    }
    console.debug('[ReceiptPreviewModal] Fetched fallback line items', fallback.length);
    const meta = {
      ...(payload.meta || {}),
      items_source: payload.meta?.items_source || 'file_store',
      items_count: fallback.length,
    };
    return {
      ...payload,
      line_items: fallback,
      meta,
    };
  } catch (err) {
    console.error('Failed to load fallback line items', err);
    return payload;
  }
}

function publishOverlayDebug(payload) {
  const boxesList = Array.isArray(payload?.boxes) ? payload.boxes : [];
  const debugPayload = {
    hasPayload: !!payload,
    orientation: payload?.meta?.image_orientation || 'unknown',
    boxesCount: boxesList.length,
    sample: boxesList.slice(0, 3),
    firstBox: boxesList[0] || null,
    allBoxes: boxesList,
  };
  console.log('[OVERLAY_DEBUG] Payload:', payload);
  console.log('[OVERLAY_DEBUG] Boxes:', boxesList);
  console.log('[OVERLAY_DEBUG] Boxes length:', boxesList.length);
  if (boxesList.length > 0) {
    console.log('[OVERLAY_DEBUG] First box:', boxesList[0]);
  }
  if (typeof window !== 'undefined') {
    window.__overlayDebug = debugPayload;
  }
}

const MOJIBAKE_PATTERN = /[ÃÂâ][\u0080-\u00FF]/;
let cachedUtf8Decoder = null;

function ensureUtf8Decoder() {
  if (cachedUtf8Decoder) {
    return cachedUtf8Decoder;
  }
  if (typeof TextDecoder === 'function') {
    try {
      cachedUtf8Decoder = new TextDecoder('utf-8', { fatal: false });
    } catch (err) {
      cachedUtf8Decoder = null;
    }
  }
  return cachedUtf8Decoder;
}

function fixMojibakeString(value) {
  if (typeof value !== 'string' || value.length === 0) {
    return value;
  }
  if (!MOJIBAKE_PATTERN.test(value)) {
    return value;
  }
  try {
    const decoder = ensureUtf8Decoder();
    if (decoder) {
      const bytes = new Uint8Array(value.length);
      for (let index = 0; index < value.length; index += 1) {
        bytes[index] = value.charCodeAt(index) & 0xff;
      }
      const decoded = decoder.decode(bytes);
      if (decoded && decoded !== value) {
        return decoded;
      }
    }
  } catch (err) {
    // Swallow and fall back
  }
  if (typeof Buffer !== 'undefined') {
    try {
      const decoded = Buffer.from(value, 'latin1').toString('utf8');
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // Ignore buffer fallback failure
    }
  }
  if (typeof decodeURIComponent === 'function' && typeof escape === 'function') {
    try {
      const decoded = decodeURIComponent(escape(value));
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // ignore
    }
  }
  return value;
}

function fixEncodingDeep(value) {
  if (typeof value === 'string') {
    return fixMojibakeString(value);
  }
  if (Array.isArray(value)) {
    return value.map((entry) => fixEncodingDeep(entry));
  }
  if (value && typeof value === 'object') {
    const next = {};
    for (const [key, nested] of Object.entries(value)) {
      next[key] = fixEncodingDeep(nested);
    }
    return next;
  }
  return value;
}

function toNullableNumber(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function toOptionalString(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return fixMojibakeString(String(value)).trim();
}

function pickFirstString(...values) {
  for (const value of values) {
    const str = toOptionalString(value);
    if (str) {
      return str;
    }
  }
  return '';
}

function pickFirstNumber(...values) {
  for (const value of values) {
    const num = toNullableNumber(value);
    if (num !== null) {
      return num;
    }
  }
  return null;
}

function splitArticlePrefix(value) {
  if (value === null || value === undefined) {
    return { article_id: '', name: '' };
  }
  const text = fixMojibakeString(String(value)).trim();
  if (!text) {
    return { article_id: '', name: '' };
  }
  const match = text.match(/^([A-Za-z0-9/_-]+)\s*[.:\-]\s*(.+)$/);
  if (match && match[1] && match[2]) {
    return { article_id: toOptionalString(match[1]), name: toOptionalString(match[2]) || '' };
  }
  return { article_id: '', name: toOptionalString(text) };
}

function normaliseReceipt(payload) {
  const sourceReceipt = payload?.receipt || {};
  const unifiedFile = payload?.unified_file || {};
  const header = payload?.header || {};
  const receipt = { ...sourceReceipt };

  const ensureString = (key, ...candidates) => {
    const current = toOptionalString(receipt[key]);
    if (current) {
      receipt[key] = current;
      return;
    }
    const candidate = pickFirstString(...candidates);
    receipt[key] = candidate;
  };

  const ensureNumber = (key, ...candidates) => {
    const current = toNullableNumber(receipt[key]);
    if (current !== null) {
      receipt[key] = current;
      return;
    }
    const candidate = pickFirstNumber(...candidates);
    receipt[key] = candidate;
  };

  ensureString(
    'merchant',
    sourceReceipt.merchant_name,
    unifiedFile.merchant,
    unifiedFile.merchant_name,
    unifiedFile.company_name
  );
  ensureString(
    'purchase_datetime',
    sourceReceipt.purchase_date,
    unifiedFile.purchase_datetime,
    unifiedFile.purchase_date,
    header.purchase_datetime,
    header.purchase_date
  );
  ensureString('receipt_number', unifiedFile.receipt_number, unifiedFile.invoice_number, header.receipt_number);
  ensureString('payment_type', unifiedFile.payment_type);
  ensureString('expense_type', unifiedFile.expense_type);
  ensureString('credit_card_number', unifiedFile.credit_card_number);
  ensureString('credit_card_last_4_digits', unifiedFile.credit_card_last_4_digits);
  ensureString('credit_card_type', unifiedFile.credit_card_type);
  ensureString('credit_card_brand_full', unifiedFile.credit_card_brand_full);
  ensureString('credit_card_brand_short', unifiedFile.credit_card_brand_short);
  ensureString('credit_card_payment_variant', unifiedFile.credit_card_payment_variant);
  ensureString('credit_card_token', unifiedFile.credit_card_token);
  ensureString('credit_card_entering_mode', unifiedFile.credit_card_entering_mode);
  ensureString('currency', unifiedFile.currency, 'SEK');

  const exchangeRate = pickFirstNumber(sourceReceipt.exchange_rate, unifiedFile.exchange_rate);
  receipt.exchange_rate = exchangeRate !== null ? exchangeRate : null;

  const grossAmount = pickFirstNumber(
    sourceReceipt.gross_amount,
    sourceReceipt.gross_amount_original,
    unifiedFile.gross_amount,
    unifiedFile.total_amount,
    unifiedFile.gross_amount_original
  );
  receipt.gross_amount = grossAmount;

  const netAmount = pickFirstNumber(
    sourceReceipt.net_amount,
    sourceReceipt.net_amount_original,
    unifiedFile.net_amount,
    unifiedFile.net_amount_original
  );
  receipt.net_amount = netAmount;

  ensureNumber(
    'gross_amount_original',
    sourceReceipt.gross_amount_original,
    unifiedFile.gross_amount_original,
    unifiedFile.total_amount,
    grossAmount
  );
  ensureNumber('net_amount_original', sourceReceipt.net_amount_original, unifiedFile.net_amount_original, netAmount);
  ensureNumber('gross_amount_sek', sourceReceipt.gross_amount_sek, unifiedFile.gross_amount_sek);
  ensureNumber('net_amount_sek', sourceReceipt.net_amount_sek, unifiedFile.net_amount_sek);
  ensureNumber('total_vat_25', sourceReceipt.total_vat_25, unifiedFile.total_vat_25);
  ensureNumber('total_vat_12', sourceReceipt.total_vat_12, unifiedFile.total_vat_12);
  ensureNumber('total_vat_6', sourceReceipt.total_vat_6, unifiedFile.total_vat_6);

  if (receipt.credit_card_match === undefined || receipt.credit_card_match === null) {
    const match = pickFirstNumber(unifiedFile.credit_card_match, 0);
    receipt.credit_card_match = match ?? 0;
  }

  return receipt;
}

function normaliseCompany(payload) {
  const company = { ...(payload?.company || {}) };
  const candidates = [
    payload?.receipt?.company,
    payload?.receipt?.merchant_details,
    payload?.unified_file?.company,
    payload?.unified_file,
  ].filter(Boolean);

  const ensure = (key, aliases = []) => {
    const current = toOptionalString(company[key]);
    if (current) {
      company[key] = current;
      return;
    }
    for (const source of candidates) {
      const keys = [key, ...aliases];
      for (const alias of keys) {
        const value = source?.[alias];
        if (value !== undefined && value !== null) {
          const str = toOptionalString(value);
          if (str) {
            company[key] = str;
            return;
          }
        }
      }
    }
    company[key] = '';
  };

  ensure('name', ['company_name', 'merchant_name', 'merchant']);
  ensure('orgnr', ['orgnr', 'org_number', 'organisation_number', 'organization_number', 'vat_number']);
  ensure('address', ['address', 'street_address', 'street']);
  ensure('address2', ['address2', 'address_line2', 'street2']);
  ensure('zip', ['zip', 'zip_code', 'postal_code', 'postnr']);
  ensure('city', ['city', 'town', 'locality', 'municipality']);
  ensure('country', ['country', 'country_name', 'country_code']);
  ensure('www', ['www', 'website', 'url', 'web']);
  ensure('phone', ['phone', 'phone_number', 'telephone', 'tel']);
  ensure('email', ['email', 'email_address']);

  return company;
}

function normaliseItems(payload) {
  const receiptCurrency = payload?.receipt?.currency || 'SEK';
  const rawItems = firstNonEmptyArray(payload, ['items', 'receipt_items', 'line_items', 'unified_file_items']);
  return rawItems.map((item) => {
    const quantity = toNullableNumber(item.number ?? item.quantity ?? item.qty) ?? 1;
    const unitNet =
      toNullableNumber(
        item.item_price_ex_vat ??
        item.unit_price_ex_vat ??
        item.price_ex_vat ??
        item.unit_amount_ex_vat ??
        item.net_price ??
        item.unit_net
      ) ?? null;
    const unitGross =
      toNullableNumber(
        item.item_price_inc_vat ??
        item.unit_price_inc_vat ??
        item.price_inc_vat ??
        item.unit_amount_inc_vat ??
        item.gross_price ??
        item.unit_gross
      ) ?? null;
    const totalNet =
      toNullableNumber(
        item.item_total_price_ex_vat ??
        item.total_price_ex_vat ??
        item.total_net ??
        item.net_amount ??
        item.amount_ex_vat ??
        item.total_ex_vat
      ) ?? (unitNet != null ? unitNet * quantity : null);
    const totalGross =
      toNullableNumber(
        item.item_total_price_inc_vat ??
        item.total_price_inc_vat ??
        item.total_gross ??
        item.gross_amount ??
        item.total_amount ??
        item.total_inc_vat
      ) ?? (unitGross != null ? unitGross * quantity : null);
    const vatAmount =
      toNullableNumber(item.vat ?? item.item_vat ?? item.vat_amount ?? item.item_vat_total ?? item.total_vat) ??
      (totalGross != null && totalNet != null ? totalGross - totalNet : null);
    const vatRate =
      toNullableNumber(item.vat_percentage ?? item.vat_rate ?? item.vat_percent ?? item.vat) ??
      (vatAmount != null && totalNet ? (vatAmount / totalNet) * 100 : null);
    const idCandidate = item.id ?? item.item_id ?? item.receipt_item_id ?? item.main_id ?? item.uuid ?? null;

    const rawName = item.name ?? item.description ?? item.item_name ?? '';
    const { article_id: parsedArticleId, name: parsedName } = splitArticlePrefix(rawName);
    let articleId = toOptionalString(
      item.article_id ?? item.articleNumber ?? item.item_code ?? item.sku ?? item.product_code ?? ''
    );
    if (!articleId && parsedArticleId) {
      articleId = parsedArticleId;
    }
    const resolvedName = parsedName || toOptionalString(rawName);

    return {
      id: idCandidate,
      item_id: item.item_id ?? item.receipt_item_id ?? null,
      article_id: articleId,
      name: resolvedName,
      number: quantity != null ? quantity : '',
      item_price_ex_vat: unitNet,
      item_price_inc_vat: unitGross,
      item_total_price_ex_vat: totalNet,
      item_total_price_inc_vat: totalGross,
      vat: vatAmount,
      vat_percentage: vatRate,
      currency: toOptionalString(item.currency ?? receiptCurrency ?? 'SEK'),
    };
  });
}

function normaliseProposals(payload, items) {
  const rawProposals = firstNonEmptyArray(payload, [
    'proposals',
    'accounting',
    'accounting_entries',
    'accounting_proposals',
    'ai_accounting_proposals',
  ]);
  if (!rawProposals.length) {
    return [];
  }

  const itemIndexById = new Map();
  items.forEach((item, index) => {
    const candidates = [
      item.id,
      item.item_id,
      item.receipt_item_id,
      item.article_id,
      item.sku,
      item.articleNumber,
    ]
      .filter((key) => key !== null && key !== undefined)
      .map((key) => String(key));
    candidates.forEach((candidate) => {
      if (!itemIndexById.has(candidate)) {
        itemIndexById.set(candidate, index);
      }
    });
  });

  return rawProposals.map((entry, index) => {
    const debit = toNullableNumber(entry.debit ?? entry.debet ?? entry.amount_debet ?? entry.amount_debit);
    const credit = toNullableNumber(entry.credit ?? entry.kredit ?? entry.amount_credit);
    const vatRate = toNullableNumber(entry.vat_rate ?? entry.vat ?? entry.vat_percentage);
    let itemIndex =
      typeof entry.item_index === 'number' && Number.isInteger(entry.item_index)
        ? entry.item_index
        : null;
    const candidateKeys = [
      entry.item_id,
      entry.receipt_item_id,
      entry.item,
      entry.item_key,
      entry.article_id,
    ]
      .filter((key) => key !== null && key !== undefined)
      .map((key) => String(key));
    if ((itemIndex === null || itemIndex < 0 || itemIndex >= items.length) && candidateKeys.length) {
      for (const candidate of candidateKeys) {
        if (itemIndexById.has(candidate)) {
          itemIndex = itemIndexById.get(candidate);
          break;
        }
      }
    }
    if (itemIndex === null || itemIndex < 0 || itemIndex >= items.length) {
      itemIndex = items.length > 0 ? Math.min(index, items.length - 1) : 0;
    }

    return {
      id: entry.id ?? entry.proposal_id ?? null,
      item_index: itemIndex,
      account: toOptionalString(entry.account ?? entry.account_code ?? entry.konto ?? ''),
      debit,
      credit,
      vat_rate: vatRate,
      notes: toOptionalString(entry.notes ?? entry.description ?? entry.memo ?? ''),
    };
  });
}

function decorateModalPayload(payload) {
  if (!payload) {
    return payload;
  }
  const receipt = normaliseReceipt(payload);
  const basePayload = { ...payload, receipt };
  const company = normaliseCompany(basePayload);
  const items = normaliseItems(basePayload);
  const proposals = normaliseProposals(basePayload, items);
  return { ...basePayload, company, items, proposals };
}

const COMPANY_FIELDS = [
  { key: 'name', label: 'Företag', source: 'company', extras: ['receipt.merchant'] },
  { key: 'orgnr', label: 'Organisationsnummer', source: 'company', extras: ['receipt.organisation_number', 'header.orgnr'] },
  { key: 'address', label: 'Adress', source: 'company', extras: ['company.address_line1'] },
  { key: 'address2', label: 'Adress 2', source: 'company', extras: ['company.address_line2'] },
  { key: 'zip', label: 'Postnummer', source: 'company', extras: ['receipt.postnr', 'receipt.postal_code'] },
  { key: 'city', label: 'Ort', source: 'company', extras: ['receipt.city'] },
  { key: 'country', label: 'Land', source: 'company', extras: ['company.country_name'] },
  { key: 'www', label: 'Hemsida', source: 'company', extras: ['company.website', 'company.url'] },
  { key: 'phone', label: 'Telefonnummer', source: 'company', extras: ['company.phone_number'] },
  { key: 'email', label: 'Email', source: 'company', extras: ['company.email_address'] },
];

const PAYMENT_FIELDS = [
  { key: 'purchase_datetime', label: 'Inköpsdatum', source: 'receipt', extras: ['receipt.purchase_date', 'header.purchase_datetime'] },
  { key: 'receipt_number', label: 'Kvittonummer', source: 'receipt', extras: ['header.receipt_number'] },
  { key: 'payment_type', label: 'Betalningstyp', source: 'receipt', extras: ['header.payment_type'] },
  { key: 'expense_type', label: 'Utgiftstyp', source: 'receipt' },
  { key: 'credit_card_number', label: 'Kortnummer', source: 'receipt', extras: ['receipt.card_number'] },
  { key: 'credit_card_last_4_digits', label: 'Kortnummer 4 sista', source: 'receipt', extras: ['receipt.card_last4'] },
  { key: 'credit_card_type', label: 'Korttyp', source: 'receipt', extras: ['receipt.card_type'] },
  { key: 'credit_card_brand_full', label: 'Korttyp full', source: 'receipt' },
  { key: 'credit_card_brand_short', label: 'Korttyp kort', source: 'receipt' },
  { key: 'credit_card_payment_variant', label: 'Betalningsvariant', source: 'receipt' },
  { key: 'credit_card_token', label: 'Korttyp token', source: 'receipt' },
  { key: 'credit_card_entering_mode', label: 'Inmatningsläge', source: 'receipt', extras: ['receipt.card_entry_mode'] },
];

const EXPENSE_TYPE_OPTIONS = [
  { value: '', label: 'Valj...' },
  { value: 'personal', label: 'personal' },
  { value: 'corporate', label: 'corporate' },
];

const PAYMENT_TYPE_OPTIONS = [
  { value: '', label: 'Valj...' },
  { value: 'card', label: 'card' },
  { value: 'swish', label: 'swish' },
  { value: 'cash', label: 'cash' },
];

const AMOUNT_FIELDS = [
  { key: 'currency', label: 'Valuta', source: 'receipt' },
  { key: 'exchange_rate', label: 'Växlingskurs', source: 'receipt' },
  { key: 'gross_amount', label: 'Originalbelopp ink. moms', source: 'receipt', format: 'currency' },
  { key: 'net_amount', label: 'Originalbelopp ex. moms', source: 'receipt', format: 'currency' },
  { key: 'gross_amount_sek', label: 'Svenskt totalbelopp ink moms SEK', source: 'receipt', format: 'currency' },
  { key: 'net_amount_sek', label: 'Svenskt totalbelopp ex. moms SEK', source: 'receipt', format: 'currency' },
  { key: 'total_vat_25', label: 'Moms 25%', source: 'receipt', format: 'currency' },
  { key: 'total_vat_12', label: 'Moms 12%', source: 'receipt', format: 'currency' },
  { key: 'total_vat_6', label: 'Moms 6%', source: 'receipt', format: 'currency' },
];

const ITEM_DETAIL_FIELDS = [
  { key: 'article_id', label: 'Artikelnummer' },
  { key: 'name', label: 'Artikel' },
  { key: 'number', label: 'Antal' },
  { key: 'currency', label: 'Valuta' },
  { key: 'item_price_ex_vat', label: 'Belopp ex. moms' },
  { key: 'item_price_inc_vat', label: 'Belopp ink. moms' },
  { key: 'vat', label: 'Belopp moms' },
  { key: 'vat_percentage', label: 'Moms %' },
  { key: 'item_total_price_ex_vat', label: 'Belopp totalt ex. moms' },
  { key: 'item_total_price_inc_vat', label: 'Belopp totalt ink. moms' },
  { key: 'item_vat_total', label: 'Belopp moms totalt', computed: true },
];

function prepareDraft(payload) {
  if (!payload) {
    return { receipt: {}, company: {}, items: [], proposals: [] };
  }
  const receipt = payload.receipt || {};
  const company = payload.company || {};
  const items = (payload.items || []).map((item) => ({
    id: item.id ?? null,
    item_id: item.item_id ?? null,
    article_id: toOptionalString(item.article_id || item.articleNumber || ''),
    name: toOptionalString(item.name || item.description || ''),
    number: item.number != null ? String(item.number) : '',
    item_price_ex_vat: item.item_price_ex_vat != null ? String(item.item_price_ex_vat) : '',
    item_price_inc_vat: item.item_price_inc_vat != null ? String(item.item_price_inc_vat) : '',
    item_total_price_ex_vat: item.item_total_price_ex_vat != null ? String(item.item_total_price_ex_vat) : '',
    item_total_price_inc_vat: item.item_total_price_inc_vat != null ? String(item.item_total_price_inc_vat) : '',
    vat: item.vat != null ? String(item.vat) : '',
    vat_percentage: item.vat_percentage != null ? String(item.vat_percentage) : '',
    currency: toOptionalString(item.currency || payload?.receipt?.currency || 'SEK'),
  }));
  const itemCount = Math.max(items.length, 1);
  const proposals = (payload.proposals || []).map((entry, index) => ({
    id: entry.id ?? null,
    account: toOptionalString(entry.account || entry.account_code || ''),
    debit: entry.debit != null ? String(entry.debit) : '',
    credit: entry.credit != null ? String(entry.credit) : '',
    vat_rate: entry.vat_rate != null ? String(entry.vat_rate) : '',
    notes: toOptionalString(entry.notes || ''),
    item_index:
      typeof entry.item_index === 'number' && entry.item_index >= 0
        ? entry.item_index
        : Math.min(index, itemCount - 1),
  }));
  return {
    receipt: {
      merchant: receipt.merchant || receipt.merchant_name || '',
      vat: receipt.vat || '',
      purchase_datetime: receipt.purchase_datetime || receipt.purchase_date || '',
      receipt_number: receipt.receipt_number || '',
      payment_type: receipt.payment_type || '',
      expense_type: receipt.expense_type || '',
      credit_card_number: receipt.credit_card_number || '',
      credit_card_last_4_digits: receipt.credit_card_last_4_digits || '',
      credit_card_type: receipt.credit_card_type || '',
      credit_card_brand_full: receipt.credit_card_brand_full || '',
      credit_card_brand_short: receipt.credit_card_brand_short || '',
      credit_card_payment_variant: receipt.credit_card_payment_variant || '',
      credit_card_token: receipt.credit_card_token || '',
      credit_card_entering_mode: receipt.credit_card_entering_mode || '',
      currency: receipt.currency || 'SEK',
      exchange_rate: receipt.exchange_rate != null ? String(receipt.exchange_rate) : '',
      gross_amount: receipt.gross_amount != null ? String(receipt.gross_amount) : '',
      net_amount: receipt.net_amount != null ? String(receipt.net_amount) : '',
      gross_amount_sek: receipt.gross_amount_sek != null ? String(receipt.gross_amount_sek) : '',
      net_amount_sek: receipt.net_amount_sek != null ? String(receipt.net_amount_sek) : '',
      total_vat_25: receipt.total_vat_25 != null ? String(receipt.total_vat_25) : '',
      total_vat_12: receipt.total_vat_12 != null ? String(receipt.total_vat_12) : '',
      total_vat_6: receipt.total_vat_6 != null ? String(receipt.total_vat_6) : '',
      ai_status: receipt.ai_status || receipt.status || '',
      ai_confidence: receipt.ai_confidence != null ? String(receipt.ai_confidence) : '',
      tags: Array.isArray(receipt.tags) ? receipt.tags.join(', ') : receipt.tags || '',
      ocr_raw: receipt.ocr_raw || '',
      other_data: receipt.other_data || '',
    },
    company: {
      name: company.name || '',
      orgnr: company.orgnr || '',
      address: company.address || '',
      address2: company.address2 || '',
      zip: company.zip || '',
      city: company.city || '',
      country: company.country || '',
      phone: company.phone || '',
      www: company.www || '',
      email: company.email || '',
    },
    items,
    proposals,
  };
}

// Format helpers
const formatDate = (dateString) => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('sv-SE');
  } catch {
    return dateString;
  }
};

const formatCurrency = (value) => {
  if (value == null || isNaN(value)) return '-';
  return new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
  }).format(value);
};

// Main component
export default function ReceiptPreviewModal({
  open,
  receipt,
  previewImage,
  onClose,
  onReceiptUpdate,
  onNavigateNext,
  onNavigatePrevious,
  hasNext = false,
  hasPrevious = false
}) {
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [restarting, setRestarting] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [payload, setPayload] = React.useState(null);
  const [draft, setDraft] = React.useState(null);
  const [editing, setEditing] = React.useState(false);
  const [hoverField, setHoverField] = React.useState(null);
  const [companySuggestions, setCompanySuggestions] = React.useState([]);
  const [selectedCompanyId, setSelectedCompanyId] = React.useState(null);
  const [isExistingCompany, setIsExistingCompany] = React.useState(false);
  const [imageViewerOpen, setImageViewerOpen] = React.useState(false);
  const [imageZoom, setImageZoom] = React.useState(1);
  const imgRef = React.useRef(null);
  const companySelectRef = React.useRef(null);
  const companyInputRef = React.useRef(null);
  const [companyDropdownOpen, setCompanyDropdownOpen] = React.useState(false);
  const [companySearchLoading, setCompanySearchLoading] = React.useState(false);
  const [companyHighlightIndex, setCompanyHighlightIndex] = React.useState(-1);
  const [currentPageIndex, setCurrentPageIndex] = React.useState(0);

  const safeReceipt = receipt ?? {};
  const safeReceiptId = safeReceipt.id ?? '';
  const shouldRender = Boolean(open && receipt);


  React.useEffect(() => {
    if (!open) {
      setPayload(null);
      setDraft(null);
      setEditing(false);
      setHoverField(null);
      setError(null);
      setLoading(false);
      setSaving(false);
      setRestarting(false);
      setCompanySuggestions([]);
      setSelectedCompanyId(null);
      setIsExistingCompany(false);
      setCompanyDropdownOpen(false);
      setCompanySearchLoading(false);
      setCompanyHighlightIndex(-1);
      setImageViewerOpen(false);
      setImageZoom(1);
      setCurrentPageIndex(0);
      publishOverlayDebug(null);
    }
  }, [open]);

  React.useEffect(() => {
    if (!imageViewerOpen) {
      return undefined;
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setImageViewerOpen(false);
      } else if ((event.ctrlKey || event.metaKey) && event.key === '0') {
        event.preventDefault();
        setImageZoom(1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [imageViewerOpen]);

  React.useEffect(() => {
    if (!open || !safeReceiptId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setEditing(false);
    setHoverField(null);
    setCurrentPageIndex(0);

    const fetchData = async () => {
      try {
        const res = await api.fetch(`/ai/api/receipts/${safeReceiptId}/modal`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        let rawPayload = await res.json();

        // KRITISKT: Applicera encoding-fix på ALL data från API INNAN vidare behandling
        rawPayload = fixEncodingDeep(rawPayload);

        rawPayload = await attachLineItemsFallback(rawPayload, safeReceiptId);
        if (cancelled) {
          return;
        }
        const decorated = decorateModalPayload(rawPayload);
        const mergedPayload = { ...rawPayload, ...decorated };
        if (cancelled) {
          return;
        }
        setPayload(mergedPayload);
        setDraft(prepareDraft(mergedPayload));
        setLoading(false);
        setSelectedCompanyId(null);
        setIsExistingCompany(false);
        setCompanyDropdownOpen(false);
        setCompanyHighlightIndex(-1);
        setCompanySuggestions([]);
        publishOverlayDebug(mergedPayload);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [open, safeReceiptId]);

  // Debounce helper function
  const debounceTimeout = React.useRef(null);
  const fetchCompanySuggestions = React.useCallback((searchTerm, options = {}) => {
    const { allowEmpty = false } = options;

    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
    }

    const trimmed = (searchTerm || '').trim();
    if (!allowEmpty && trimmed.length === 0) {
      setCompanySuggestions([]);
      setCompanySearchLoading(false);
      setCompanyHighlightIndex(-1);
      return;
    }

    setCompanySearchLoading(true);

    debounceTimeout.current = setTimeout(async () => {
      try {
        const params = new URLSearchParams();
        if (trimmed.length > 0) {
          params.set('search', trimmed);
          params.set('limit', '20');
        } else {
          params.set('limit', '10');
        }
        const res = await api.fetch(`/ai/api/companies?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setCompanySuggestions(Array.isArray(data) ? data : []);
        } else {
          setCompanySuggestions([]);
        }
      } catch (err) {
        console.error('Failed to fetch company suggestions', err);
        setCompanySuggestions([]);
      } finally {
        setCompanySearchLoading(false);
      }
    }, 300);
  }, []);

  React.useEffect(() => {
    return () => {
      if (debounceTimeout.current) {
        clearTimeout(debounceTimeout.current);
      }
    };
  }, []);

  const boxes = payload?.boxes || [];

  const matchHighlight = (key) => {
    if (!hoverField || !key) {
      return '';
    }
    if (hoverField === key) {
      return 'highlighted';
    }
    const normalisedHover = normaliseFieldId(hoverField);
    const normalisedKey = normaliseFieldId(key);
    if (normalisedHover !== normalisedKey) {
      return 'muted';
    }
    const hoverHasIndex = /\[\d+\]/.test(hoverField);
    const keyHasIndex = /\[\d+\]/.test(key);
    if (hoverHasIndex || keyHasIndex) {
      return 'muted';
    }
    return 'highlighted';
  };

  const receiptData = payload?.receipt || {};
  const receiptDraft = draft?.receipt || {};
  const companyData = payload?.company || {};
  const companyDraft = draft?.company || {};

  const companyNameValue = companyDraft.name ?? '';
  const trimmedCompanyName = companyNameValue.trim();
  const normalisedSuggestions = Array.isArray(companySuggestions) ? companySuggestions : [];
  const showCreateOption =
    !isExistingCompany &&
    trimmedCompanyName.length >= 1 &&
    !normalisedSuggestions.some(
      (suggestion) => (suggestion?.name || '').toLowerCase() === trimmedCompanyName.toLowerCase()
    );
  const dropdownOptions = [
    ...normalisedSuggestions.map((suggestion) => ({
      type: 'company',
      data: suggestion,
    })),
    ...(showCreateOption ? [{ type: 'create', data: { name: trimmedCompanyName } }] : []),
  ];
  const dropdownOptionsLength = dropdownOptions.length;

  React.useEffect(() => {
    if (!dropdownOptionsLength) {
      setCompanyHighlightIndex(-1);
      return;
    }
    setCompanyHighlightIndex((prev) => {
      if (prev >= 0 && prev < dropdownOptionsLength) {
        return prev;
      }
      return 0;
    });
  }, [dropdownOptionsLength]);

  React.useEffect(() => {
    if (!companyDropdownOpen) {
      return;
    }
    if (typeof document === 'undefined') {
      return;
    }
    const handleClickOutside = (event) => {
      if (!companySelectRef.current) {
        return;
      }
      if (companySelectRef.current.contains(event.target)) {
        return;
      }
      setCompanyDropdownOpen(false);
      setCompanyHighlightIndex(-1);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [companyDropdownOpen]);

  const itemsSource = editing && draft ? draft.items : payload?.items || [];
  const proposalsSource = editing && draft ? draft.proposals : payload?.proposals || [];

  const proposalsByItem = (() => {
    if (!itemsSource.length) {
      return [];
    }
    const groups = itemsSource.map(() => []);
    proposalsSource.forEach((entry, index) => {
      const targetIndex =
        typeof entry.item_index === 'number' && entry.item_index >= 0 && entry.item_index < groups.length
          ? entry.item_index
          : Math.min(groups.length - 1, Math.max(index, 0));
      groups[targetIndex].push({ ...entry, _globalIndex: index });
    });
    return groups;
  })();

  const updateReceiptDraft = (field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      return { ...prev, receipt: { ...prev.receipt, [field]: value } };
    });
  };

  const updateCompanyDraft = (field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      return { ...prev, company: { ...prev.company, [field]: value } };
    });
  };

  const updateItemDraft = (index, field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      const nextItems = prev.items.map((item, idx) => (idx === index ? { ...item, [field]: value } : item));
      return { ...prev, items: nextItems };
    });
  };

  const updateProposalDraft = (index, field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      const nextProposals = prev.proposals.map((proposal, idx) =>
        idx === index ? { ...proposal, [field]: value } : proposal
      );
      return { ...prev, proposals: nextProposals };
    });
  };

  const handleCompanyInputFocus = (event) => {
    if (event?.target?.select) {
      event.target.select();
    }
    if (isExistingCompany) {
      // Allow editing fields for an existing company without reopening dropdown
      return;
    }
    setCompanyDropdownOpen(true);
    fetchCompanySuggestions(companyNameValue, { allowEmpty: true });
  };

  const handleCompanyInputChange = (event) => {
    const nextValue = event.target.value;
    updateCompanyDraft('name', nextValue);
    if (isExistingCompany) {
      // Editing current company fields; keep selection and avoid suggestion search
      return;
    }
    setSelectedCompanyId(null);
    setIsExistingCompany(false);
    setCompanyDropdownOpen(true);
    setCompanyHighlightIndex(-1);
    if (nextValue.trim().length === 0) {
      fetchCompanySuggestions('', { allowEmpty: true });
    } else {
      fetchCompanySuggestions(nextValue);
    }
  };

  const handleCompanyDropdownToggle = () => {
    if (isExistingCompany) {
      return;
    }
    setCompanyDropdownOpen((prev) => {
      const nextState = !prev;
      if (nextState) {
        fetchCompanySuggestions(companyNameValue, { allowEmpty: true });
        if (companyInputRef.current) {
          companyInputRef.current.focus();
          companyInputRef.current.select();
        }
      }
      if (!nextState) {
        setCompanyHighlightIndex(-1);
      }
      return nextState;
    });
  };

  const handleSelectExistingCompany = async (company) => {
    setCompanyDropdownOpen(false);
    setCompanyHighlightIndex(-1);
    setCompanySuggestions([]);
    setCompanySearchLoading(false);
    try {
      const res = await api.fetch(`/ai/api/companies/${company.id}`);
      if (res.ok) {
        const fullCompanyData = await res.json();
        setDraft((prev) => {
          if (!prev) {
            return prev;
          }
          return {
            ...prev,
            company: {
              name: fullCompanyData.name || '',
              orgnr: fullCompanyData.orgnr || '',
              address: fullCompanyData.address || '',
              address2: fullCompanyData.address2 || '',
              zip: fullCompanyData.zip || '',
              city: fullCompanyData.city || '',
              country: fullCompanyData.country || '',
              phone: fullCompanyData.phone || '',
              www: fullCompanyData.www || '',
              email: fullCompanyData.email || '',
            },
          };
        });
        setSelectedCompanyId(company.id);
        setIsExistingCompany(true);
      }
    } catch (err) {
      console.error('Failed to fetch company details', err);
    }
  };

  const handleCreateNewCompany = (name) => {
    updateCompanyDraft('name', name);
    setSelectedCompanyId(null);
    setIsExistingCompany(false);
    setCompanyDropdownOpen(false);
    setCompanySuggestions([]);
    setCompanyHighlightIndex(-1);
    setCompanySearchLoading(false);
  };

  const handleCompanyKeyDown = (event) => {
    if (isExistingCompany) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!companyDropdownOpen) {
        setCompanyDropdownOpen(true);
        if (companyNameValue) {
          fetchCompanySuggestions(companyNameValue);
        }
        return;
      }
      if (!dropdownOptionsLength) {
        return;
      }
      setCompanyHighlightIndex((prev) => {
        const next = prev + 1;
        if (next >= dropdownOptionsLength) {
          return 0;
        }
        return next;
      });
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (!companyDropdownOpen || !dropdownOptionsLength) {
        return;
      }
      setCompanyHighlightIndex((prev) => {
        const next = prev - 1;
        if (next < 0) {
          return dropdownOptionsLength - 1;
        }
        return next;
      });
      return;
    }
    if (event.key === 'Enter') {
      if (!companyDropdownOpen) {
        if (dropdownOptionsLength) {
          setCompanyDropdownOpen(true);
        } else if (trimmedCompanyName) {
          handleCreateNewCompany(trimmedCompanyName);
        }
        event.preventDefault();
        return;
      }
      const option = dropdownOptions[companyHighlightIndex];
      if (option) {
        event.preventDefault();
        if (option.type === 'company') {
          handleSelectExistingCompany(option.data);
        } else {
          handleCreateNewCompany(option.data.name);
        }
      }
      return;
    }
    if (event.key === 'Escape') {
      if (companyDropdownOpen) {
        event.preventDefault();
        setCompanyDropdownOpen(false);
        setCompanyHighlightIndex(-1);
      }
    }
  };

  const handleUnlockCompanyFields = () => {
    setIsExistingCompany(false);
    setSelectedCompanyId(null);
    setCompanyDropdownOpen(false);
    setCompanySuggestions([]);
    setCompanyHighlightIndex(-1);
    setCompanySearchLoading(false);
    if (companyInputRef.current) {
      companyInputRef.current.focus();
      companyInputRef.current.select();
    }
    fetchCompanySuggestions(companyDraft.name ?? '', { allowEmpty: true });
  };

  const handleToggleEdit = () => {
    if (editing) {
      // Exiting edit mode - reset to original payload when canceling
      setDraft(prepareDraft(payload));
      setSelectedCompanyId(null);
      setCompanySuggestions([]);
      setCompanyDropdownOpen(false);
      setCompanyHighlightIndex(-1);
      setCompanySearchLoading(false);
      setIsExistingCompany(false);
    } else {
      // Entering edit mode - keep any selected company but start with a clean dropdown state
      setCompanyDropdownOpen(false);
      setCompanyHighlightIndex(-1);
      setCompanySuggestions([]);
      setCompanySearchLoading(false);
    }
    setEditing((prev) => !prev);
  };

  const handleSave = async () => {
    if (!draft || !safeReceiptId) {
      if (!safeReceiptId) {
        setError('Kvitto-id saknas');
      }
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // Include company_id if existing company was selected from autocomplete
      const savePayload = {
        ...draft,
        ...(isExistingCompany && selectedCompanyId !== null ? { company_id: selectedCompanyId } : {}),
      };

      const res = await api.fetch(`/ai/api/receipts/${safeReceiptId}/modal`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(savePayload),
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !json) {
        const message = (json && (json.message || json.error)) || `HTTP ${res.status}`;
        throw new Error(message);
      }
      if (!json.receipt_updated && !json.company_updated && !json.items_updated && !json.proposals_updated) {
        throw new Error('Ändringarna kunde inte sparas. Försök igen.');
      }
      let refreshedPayload = json.data || {};

      // KRITISKT: Applicera encoding-fix på uppdaterad data
      refreshedPayload = fixEncodingDeep(refreshedPayload);

      refreshedPayload = await attachLineItemsFallback(refreshedPayload, safeReceiptId);
      const decorated = decorateModalPayload(refreshedPayload);
      const nextPayload = {
        ...(payload || {}),
        ...refreshedPayload,
        receipt: decorated.receipt || payload?.receipt || {},
        company: decorated.company || payload?.company || {},
        items: decorated.items || [],
        proposals: decorated.proposals || [],
      };
      setPayload(nextPayload);
      setDraft(prepareDraft(nextPayload));
      setEditing(false);
      setHoverField(null);
      setSelectedCompanyId(null);
      setIsExistingCompany(false);
      setCompanyDropdownOpen(false);
      setCompanyHighlightIndex(-1);
      setCompanySuggestions([]);
      setCompanySearchLoading(false);
      if (decorated.receipt && typeof onReceiptUpdate === 'function') {
        onReceiptUpdate(decorated.receipt);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget && !saving) {
      onClose();
    }
  };

  const handleNavigatePrevious = () => {
    if (hasPrevious && onNavigatePrevious && !saving && !editing) {
      onNavigatePrevious();
    }
  };

  const handleNavigateNext = () => {
    if (hasNext && onNavigateNext && !saving && !editing) {
      onNavigateNext();
    }
  };

  // Keyboard navigation
  React.useEffect(() => {
    if (!open || editing || saving) {
      return;
    }
    const handleKeyDown = (event) => {
      if (event.key === 'ArrowLeft') {
        handleNavigatePrevious();
      } else if (event.key === 'ArrowRight') {
        handleNavigateNext();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, editing, saving, hasPrevious, hasNext]);

  const handleDelete = async () => {
    if (!safeReceiptId) {
      return;
    }
    try {
      const res = await api.fetch(`/ai/api/receipts/${safeReceiptId}`, {
        method: 'DELETE'
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !json?.deleted) {
        const message = (json && (json.message || json.error)) || `HTTP ${res.status}`;
        throw new Error(message);
      }
      // Notify parent to handle navigation after deletion
      if (typeof onReceiptUpdate === 'function') {
        onReceiptUpdate({ id: safeReceiptId, deleted: true, shouldNavigateNext: hasNext });
      }

      // If no next receipt available, close modal
      if (!hasNext) {
        onClose();
      }
      // Parent will handle navigation to next receipt if shouldNavigateNext is true
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRestartAI = async () => {
    if (!safeReceiptId) {
      return;
    }
    setRestarting(true);
    setError(null);
    try {
      const res = await api.fetch(`/ai/api/receipts/${safeReceiptId}/restart-ai`, {
        method: 'POST'
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !json?.success) {
        const message = (json && (json.message || json.error)) || `HTTP ${res.status}`;
        throw new Error(message);
      }
      // Show success message by temporarily setting a success state
      // For now, just clear any existing error
      setError(null);
      // Optionally notify parent that workflow was restarted
      if (typeof onReceiptUpdate === 'function') {
        onReceiptUpdate({ id: safeReceiptId, workflow_restarted: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRestarting(false);
    }
  };

  const handleOpenImageViewer = () => {
    setImageZoom(1);
    setImageViewerOpen(true);
  };

  const handleCloseImageViewer = () => {
    setImageViewerOpen(false);
  };

  const handleImageViewerWheel = (event) => {
    if (!event.ctrlKey && !event.metaKey) {
      return;
    }
    event.preventDefault();
    const direction = event.deltaY > 0 ? -1 : 1;
    const step = 0.1 * direction;
    setImageZoom((prev) => {
      const next = prev + step;
      if (next < 0.2) {
        return 0.2;
      }
      if (next > 5) {
        return 5;
      }
      return Number(next.toFixed(2));
    });
  };

  const handleResetImageZoom = () => setImageZoom(1);

  const pages = (() => {
    const rawPages = payload?.pages ?? payload?.other_data?.pages;
    if (!Array.isArray(rawPages)) {
      return [];
    }

    const mapped = rawPages
      .map((entry, index) => {
        if (typeof entry === 'string') {
          return { filename: entry, page_number: index + 1 };
        }
        if (!entry || typeof entry !== 'object') {
          return null;
        }
        const fileId = entry.file_id ?? entry.fileId ?? entry.id ?? null;
        const pageNumberCandidate = entry.page_number ?? entry.pageNumber ?? entry.page ?? index + 1;
        const pageNumber = Number.isFinite(Number(pageNumberCandidate)) ? Number(pageNumberCandidate) : index + 1;
        const filename = entry.filename ?? entry.file_name ?? null;
        if (!fileId && !filename) {
          return null;
        }
        return { file_id: fileId, filename, page_number: pageNumber };
      })
      .filter(Boolean);

    mapped.sort((a, b) => (a.page_number ?? 0) - (b.page_number ?? 0));
    return mapped;
  })();

  const hasMultiplePages = pages.length > 1;

  React.useEffect(() => {
    if (!hasMultiplePages) {
      if (currentPageIndex !== 0) {
        setCurrentPageIndex(0);
      }
      return;
    }
    if (currentPageIndex > pages.length - 1) {
      setCurrentPageIndex(0);
    }
  }, [hasMultiplePages, pages.length, currentPageIndex]);

  const currentPage = pages[currentPageIndex] || null;
  const pageImageId = currentPage?.file_id || null;
  const pageFilename = currentPage?.filename || null;

  const baseImageSrc = safeReceiptId
    ? hasMultiplePages
      ? pageImageId
        ? `/ai/api/receipts/${pageImageId}/image?size=preview&rotate=portrait`
        : `/ai/api/receipts/${safeReceiptId}/image?size=preview&rotate=portrait${pageFilename ? `&filename=${pageFilename}` : ''}`
      : previewImage
        ? previewImage
        : `/ai/api/receipts/${safeReceiptId}/image?size=preview&rotate=portrait`
    : null;

  const handlePrevPage = () => {
    setCurrentPageIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextPage = () => {
    setCurrentPageIndex((prev) => Math.min(pages.length - 1, prev + 1));
  };

  if (!shouldRender) {
    return null;
  }

  return (
    <>
      <div className="modal-backdrop receipt-preview-modal" role="dialog" aria-label={`Förhandsgranskning kvitto ${receipt.id}`} onClick={handleBackdrop}>
        {/* Navigation arrows */}
        {hasPrevious && !editing && (
          <button
            type="button"
            className="modal-nav-arrow modal-nav-arrow-left"
            onClick={handleNavigatePrevious}
            disabled={saving}
            aria-label="Föregående kvitto"
            title="Föregående kvitto (←)"
          >
            <FiChevronLeft />
          </button>
        )}
        {hasNext && !editing && (
          <button
            type="button"
            className="modal-nav-arrow modal-nav-arrow-right"
            onClick={handleNavigateNext}
            disabled={saving}
            aria-label="Nästa kvitto"
            title="Nästa kvitto (→)"
          >
            <FiChevronRight />
          </button>
        )}
        <div className="modal modal-xxl" onClick={(event) => event.stopPropagation()}>
          <div className="modal-header">
            <div>
              <h3>Förhandsgranska kvitto</h3>
              <p className="card-subtitle">
                {receiptData.merchant || safeReceipt.merchant || 'Kvitto'} • {formatDate(receiptData.purchase_datetime)}
              </p>
              {(safeReceipt.credit_card_match || receiptData.credit_card_match) && (
                <span className="status-badge status-passed mt-2 inline-flex items-center gap-2 text-xs">
                  <FiCreditCard className="text-sm" />
                  Kortmatchat
                </span>
              )}
            </div>
            <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng förhandsgranskning" disabled={saving}>
              <FiX />
            </button>
          </div>
          <div className="modal-body receipt-modal-body">
            {loading ? (
              <div className="receipt-modal-loading">
                <div className="loading-inline">
                  <div className="loading-spinner" />
                  <span>Laddar kvitto...</span>
                </div>
              </div>
            ) : error ? (
              <div className="alert alert-error">
                <span>{error}</span>
              </div>
            ) : !payload ? (
              <div className="receipt-modal-loading">Ingen data tillgänglig</div>
            ) : (
              <div className="receipt-modal-content">
                {/* Left Column - Company & Receipt Data */}
                <div className="receipt-modal-column receipt-modal-left">
                  {/* RP5: Grunddata (Box 1) - Company Information */}
                  <div className="receipt-modal-section">
                    <h4>Grunddata (Företagsinformation)</h4>
                    <div className="receipt-modal-grid">
                      {COMPANY_FIELDS.map((field) => {
                        const sourceData = field.source === 'company' ? companyData : receiptData;
                        const draftData = field.source === 'company' ? companyDraft : receiptDraft;
                        const candidates = buildHoverCandidates(field.key, {
                          source: field.source,
                          extras: field.extras
                        });
                        const hoverKey = resolveBoxField(boxes, candidates);
                        const highlightKey = hoverKey || candidates[0] || field.key;
                        const readonlyValue =
                          sourceData[field.key] ??
                          (field.source === 'company' ? receiptData[field.key] : companyData[field.key]) ??
                          '';
                        return (
                          <div
                            key={field.key}
                            className={`receipt-modal-field ${matchHighlight(highlightKey)}`}
                            onMouseEnter={() => setHoverField(highlightKey)}
                            onMouseLeave={() => setHoverField(null)}
                          >
                            <label className="field-label" htmlFor={`field-${field.source}-${field.key}`}>
                              {field.label}
                            </label>
                            {editing ? (
                              field.key === 'name' && field.source === 'company' ? (
                                <div className={`company-select-wrapper${isExistingCompany ? ' company-select-wrapper--locked' : ''}`} ref={companySelectRef}>
                                  <div className={`company-select ${companyDropdownOpen ? 'open' : ''}`}>
                                    <input
                                      id={`field-${field.source}-${field.key}`}
                                      className="dm-input company-select-input"
                                      type="text"
                                      ref={companyInputRef}
                                      value={companyDraft.name ?? ''}
                                      onFocus={handleCompanyInputFocus}
                                      onChange={handleCompanyInputChange}
                                      onKeyDown={handleCompanyKeyDown}
                                      placeholder="Sök eller skapa företag..."
                                      disabled={saving}
                                      aria-expanded={companyDropdownOpen}
                                      aria-haspopup="listbox"
                                      autoComplete="off"
                                    />
                                    {!isExistingCompany && (
                                      <button
                                        type="button"
                                        className="company-select-toggle"
                                        onClick={handleCompanyDropdownToggle}
                                        aria-label={companyDropdownOpen ? 'Stäng företagslistan' : 'Visa företagslistan'}
                                        disabled={saving}
                                      >
                                        <FiChevronDown />
                                      </button>
                                    )}
                                  </div>
                                  {isExistingCompany ? (
                                    <button type="button" className="company-select-clear" onClick={handleUnlockCompanyFields} disabled={saving}>
                                      Byt företag
                                    </button>
                                  ) : (
                                    companyDropdownOpen && (
                                      <div className="company-dropdown" role="listbox">
                                        {companySearchLoading && (
                                          <div className="company-dropdown-status">Söker företag...</div>
                                        )}
                                        {!companySearchLoading && dropdownOptionsLength === 0 && trimmedCompanyName.length < 2 && (
                                          <div className="company-dropdown-status">Skriv minst två tecken för att söka</div>
                                        )}
                                        {!companySearchLoading && dropdownOptionsLength === 0 && trimmedCompanyName.length >= 2 && (
                                          <div className="company-dropdown-status">Inga företag matchar sökningen</div>
                                        )}
                                        {!companySearchLoading && dropdownOptionsLength > 0 && (
                                          <ul className="company-dropdown-list">
                                            {dropdownOptions.map((option, index) => {
                                              const isActive = index === companyHighlightIndex;
                                              if (option.type === 'company') {
                                                const metaParts = [option.data.orgnr, option.data.city].filter(Boolean);
                                                return (
                                                  <li
                                                    key={option.data.id}
                                                    className={`company-dropdown-item ${isActive ? 'active' : ''}`}
                                                    onMouseDown={(event) => {
                                                      event.preventDefault();
                                                      handleSelectExistingCompany(option.data);
                                                    }}
                                                    onMouseEnter={() => setCompanyHighlightIndex(index)}
                                                  >
                                                    <span className="company-dropdown-name">{option.data.name}</span>
                                                    {metaParts.length > 0 && (
                                                      <span className="company-dropdown-meta">{metaParts.join(' • ')}</span>
                                                    )}
                                                  </li>
                                                );
                                              }
                                              return (
                                                <li
                                                  key="new-company-option"
                                                  className={`company-dropdown-item create-option ${isActive ? 'active' : ''}`}
                                                  onMouseDown={(event) => {
                                                    event.preventDefault();
                                                    handleCreateNewCompany(option.data.name);
                                                  }}
                                                  onMouseEnter={() => setCompanyHighlightIndex(index)}
                                                >
                                                  Skapa nytt företag: <span className="company-dropdown-name">"{option.data.name}"</span>
                                                </li>
                                              );
                                            })}
                                          </ul>
                                        )}
                                      </div>
                                    )
                                  )}
                                </div>
                              ) : (
                                <input
                                  id={`field-${field.source}-${field.key}`}
                                  className="dm-input"
                                  value={draftData[field.key] ?? ''}
                                  onChange={(event) =>
                                    field.source === 'company'
                                      ? updateCompanyDraft(field.key, event.target.value)
                                      : updateReceiptDraft(field.key, event.target.value)
                                  }
                                  disabled={saving}
                                />
                              )
                            ) : (
                              <div className="field-value">{readonlyValue || '-'}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* RP6: Betalningstyp (Box 2) - Payment Information */}
                  <div className="receipt-modal-section">
                    <h4>Betalningstyp</h4>
                    <div className="receipt-modal-grid">
                      {PAYMENT_FIELDS.map((field) => {
                        const candidates = buildHoverCandidates(field.key, {
                          source: field.source,
                          extras: field.extras
                        });
                        const hoverKey = resolveBoxField(boxes, candidates);
                        const highlightKey = hoverKey || candidates[0] || field.key;
                        return (
                          <div
                            key={field.key}
                            className={`receipt-modal-field ${matchHighlight(highlightKey)}`}
                            onMouseEnter={() => setHoverField(highlightKey)}
                            onMouseLeave={() => setHoverField(null)}
                          >
                            <label className="field-label" htmlFor={`field-${field.source}-${field.key}`}>
                              {field.label}
                            </label>
                            {editing ? (
                              field.key === 'expense_type' ? (
                                <select
                                  id={`field-${field.source}-${field.key}`}
                                  className="dm-input"
                                  value={receiptDraft[field.key] ?? ''}
                                  onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                                  disabled={saving}
                                >
                                  {EXPENSE_TYPE_OPTIONS.map((option) => (
                                    <option key={option.value} value={option.value}>
                                      {option.label}
                                    </option>
                                  ))}
                                </select>
                              ) : field.key === 'payment_type' ? (
                                <select
                                  id={`field-${field.source}-${field.key}`}
                                  className="dm-input"
                                  value={receiptDraft[field.key] ?? ''}
                                  onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                                  disabled={saving}
                                >
                                  {PAYMENT_TYPE_OPTIONS.map((option) => (
                                    <option key={option.value} value={option.value}>
                                      {option.label}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <input
                                  id={`field-${field.source}-${field.key}`}
                                  className="dm-input"
                                  value={receiptDraft[field.key] ?? ''}
                                  onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                                  disabled={saving}
                                />
                              )
                            ) : field.key === 'purchase_datetime' ? (
                              <div className="field-value">{formatDate(receiptData.purchase_datetime)}</div>
                            ) : (
                              <div className="field-value">{receiptData[field.key] || '-'}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* RP7: Belopp (Box 3) - Amounts and VAT */}
                  <div className="receipt-modal-section">
                    <h4>Belopp</h4>
                    <div className="receipt-modal-grid">
                      {AMOUNT_FIELDS.map((field) => {
                        const candidates = buildHoverCandidates(field.key, {
                          source: field.source,
                          extras: field.extras
                        });
                        const hoverKey = resolveBoxField(boxes, candidates);
                        const highlightKey = hoverKey || candidates[0] || field.key;
                        return (
                          <div
                            key={field.key}
                            className={`receipt-modal-field ${matchHighlight(highlightKey)}`}
                            onMouseEnter={() => setHoverField(highlightKey)}
                            onMouseLeave={() => setHoverField(null)}
                          >
                            <label className="field-label" htmlFor={`field-${field.source}-${field.key}`}>
                              {field.label}
                            </label>
                            {editing ? (
                              <input
                                id={`field-${field.source}-${field.key}`}
                                className="dm-input"
                                value={receiptDraft[field.key] ?? ''}
                                onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                                disabled={saving}
                              />
                            ) : field.format === 'currency' ? (
                              <div className="field-value">{formatCurrency(Number(receiptData[field.key] || 0))}</div>
                            ) : (
                              <div className="field-value">{receiptData[field.key] || '-'}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* RP8: Övrigt (Box 4) - Other Data (Full Width) */}
                  <div className="receipt-modal-section">
                    <h4>Övrigt</h4>
                    {(() => {
                      const otherCandidates = buildHoverCandidates('other_data', {
                        source: 'receipt',
                        extras: ['receipt.notes', 'notes']
                      });
                      const otherHoverKey = resolveBoxField(boxes, otherCandidates);
                      const otherHighlightKey = otherHoverKey || otherCandidates[0] || 'other_data';
                      return (
                        <div
                          className={`receipt-modal-field ${matchHighlight(otherHighlightKey)}`}
                          onMouseEnter={() => setHoverField(otherHighlightKey)}
                          onMouseLeave={() => setHoverField(null)}
                        >
                          <label className="field-label" htmlFor="field-receipt-other_data">
                            Övrig data
                          </label>
                          {editing ? (
                            <textarea
                              id="field-receipt-other_data"
                              className="dm-input"
                              value={receiptDraft.other_data ?? ''}
                              onChange={(event) => updateReceiptDraft('other_data', event.target.value)}
                              disabled={saving}
                              rows={3}
                              style={{ width: '100%', resize: 'vertical' }}
                            />
                          ) : (
                            <div className="field-value" style={{ whiteSpace: 'pre-wrap' }}>
                              {receiptData.other_data || '-'}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>

                  {/* OCR Text Section */}
                  {editing && (
                    <div className="receipt-modal-section ocr-section">
                      <h4>OCR-text</h4>
                      <div className="ocr-content" style={{ whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto' }}>
                        {receiptDraft.ocr_raw || 'Ingen OCR-data tillgänglig'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Center Column - Image */}
                <div className="receipt-modal-center">
                  <div className="receipt-modal-image-toolbar">
                    {hasMultiplePages && (
                      <div className="receipt-modal-page-indicator text-sm font-medium whitespace-nowrap mr-4">
                        Sida {currentPageIndex + 1} av {pages.length}
                      </div>
                    )}
                    <button
                      type="button"
                      className="btn btn-text"
                      onClick={handleOpenImageViewer}
                      disabled={!baseImageSrc}
                    >
                      Visa stor bild
                    </button>
                  </div>
                  <div className="receipt-modal-image-wrapper">
                    {baseImageSrc ? (
                      <div className="receipt-modal-image-stage">
                        {hasMultiplePages && currentPageIndex > 0 && (
                          <button
                            type="button"
                            className="receipt-modal-page-arrow left"
                            onClick={handlePrevPage}
                            aria-label="Föregående sida"
                            title="Föregående sida"
                          >
                            <FiChevronLeft />
                          </button>
                        )}
                        {hasMultiplePages && currentPageIndex < pages.length - 1 && (
                          <button
                            type="button"
                            className="receipt-modal-page-arrow right"
                            onClick={handleNextPage}
                            aria-label="Nästa sida"
                            title="Nästa sida"
                          >
                            <FiChevronRight />
                          </button>
                        )}
                        <img
                          ref={imgRef}
                          src={baseImageSrc}
                          alt={`Kvitto ${safeReceiptId || ''}`}
                          className="receipt-modal-image"
                        />
                        {currentPageIndex === 0 && boxes.map((box, index) => {
                          const overlayKey = box.field || `box-${index}`;
                          const toCss = (val) => {
                            if (typeof val !== 'number') {
                              return '0%';
                            }
                            if (val > 1) {
                              return `${val}px`;
                            }
                            const clamped = Math.min(Math.max(val, 0), 1);
                            return `${clamped * 100}%`;
                          };
                          return (
                            <div
                              key={`${overlayKey}-${index}`}
                              className={`receipt-modal-overlay ${matchHighlight(overlayKey)}`}
                              style={{
                                position: 'absolute',
                                top: toCss(box.y ?? box.top ?? 0),
                                left: toCss(box.x ?? box.left ?? 0),
                                width: toCss(box.w ?? box.width ?? 0),
                                height: toCss(box.h ?? box.height ?? 0),
                              }}
                              onMouseEnter={() => setHoverField(overlayKey)}
                              onMouseLeave={() => setHoverField(null)}
                            />
                          );
                        })}
                      </div>
                    ) : (
                      <div className="receipt-modal-image-fallback">Ingen bild</div>
                    )}
                  </div>
                </div>

                {/* RP9: Items Table with Accounting (Right Column) */}
                <div className="receipt-modal-column receipt-modal-right">
                  <div className="receipt-modal-section">
                    <div className="receipt-item-header-main">Varor och kontering</div>
                    {itemsSource.length === 0 ? (
                      <div className="field-value muted">Inga varor registrerade</div>
                    ) : (
                      itemsSource.map((item, itemIndex) => {
                        const itemProposals = proposalsByItem[itemIndex] || [];
                        const itemDraft = editing && draft ? draft.items[itemIndex] : null;
                        const getItemValue = (key) => {
                          if (editing && itemDraft && Object.prototype.hasOwnProperty.call(itemDraft, key)) {
                            return itemDraft[key];
                          }
                          return item[key];
                        };
                        return (
                          <div key={`item-${itemIndex}`} className="receipt-item-card-new">
                            <div className="receipt-item-header-new">RAD {itemIndex + 1}</div>
                            <div className="receipt-item-grid-new">
                              {ITEM_DETAIL_FIELDS.map((field) => {
                                const computedValue =
                                  field.computed && field.key === 'item_vat_total'
                                    ? (() => {
                                      const grossTotal = Number(
                                        getItemValue('item_total_price_inc_vat') ?? getItemValue('item_price_inc_vat') ?? 0
                                      );
                                      const netTotal = Number(
                                        getItemValue('item_total_price_ex_vat') ?? getItemValue('item_price_ex_vat') ?? 0
                                      );
                                      const diff = grossTotal - netTotal;
                                      if (Number.isFinite(diff) && Math.abs(diff) > 0) {
                                        return diff.toFixed(2);
                                      }
                                      const fallback = Number(getItemValue('vat') || 0) * Number(getItemValue('number') || 1);
                                      return Number.isFinite(fallback) && Math.abs(fallback) > 0 ? fallback.toFixed(2) : '';
                                    })()
                                    : null;
                                const readOnlyValue = field.computed ? computedValue : getItemValue(field.key);
                                const draftValue = itemDraft ? itemDraft[field.key] ?? '' : '';
                                const itemFieldKey = `items[${itemIndex}].${field.key}`;
                                const candidates = buildHoverCandidates(field.key, {
                                  source: 'items',
                                  extras: field.extras || [],
                                  index: itemIndex
                                });
                                const hoverKey = resolveBoxField(boxes, candidates);
                                const highlightKey = hoverKey || candidates[0] || itemFieldKey;
                                return (
                                  <div
                                    key={`${field.key}-${itemIndex}`}
                                    className={`receipt-item-cell-new ${matchHighlight(highlightKey)}`}
                                    onMouseEnter={() => setHoverField(highlightKey)}
                                    onMouseLeave={() => setHoverField(null)}
                                  >
                                    <span className="cell-label-new">{field.label}</span>
                                    {editing && !field.computed ? (
                                      <input
                                        className="dm-input-new"
                                        value={draftValue}
                                        onChange={(event) => updateItemDraft(itemIndex, field.key, event.target.value)}
                                        disabled={saving}
                                      />
                                    ) : (
                                      <div className="cell-value-new">{readOnlyValue !== null && readOnlyValue !== undefined && readOnlyValue !== '' ? readOnlyValue : '-'}</div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>

                            <div className="proposal-group-new">
                              <div className="proposal-group-header-new">Kontering</div>
                              {itemProposals.length === 0 ? (
                                <div className="proposal-empty-new">Inga konteringsförslag</div>
                              ) : (
                                itemProposals.map((proposal) => {
                                  const globalIndex = proposal._globalIndex;
                                  const proposalDraft = editing && draft ? draft.proposals[globalIndex] : null;
                                  const debitValue = proposalDraft ? proposalDraft.debit : proposal.debit;
                                  const creditValue = proposalDraft ? proposalDraft.credit : proposal.credit;
                                  const accountValue = proposalDraft ? proposalDraft.account : proposal.account;
                                  const vatRateValue = proposalDraft ? proposalDraft.vat_rate : proposal.vat_rate;
                                  const notesValue = proposalDraft ? proposalDraft.notes : proposal.notes;

                                  const isDebit = Number(debitValue || 0) > 0;
                                  const amount = isDebit ? debitValue : creditValue;
                                  const amountDisplay = editing
                                    ? amount ?? ''
                                    : amount != null && amount !== ''
                                      ? formatCurrency(Number(amount))
                                      : '-';
                                  const vatRateDisplay = editing
                                    ? vatRateValue ?? ''
                                    : vatRateValue != null && vatRateValue !== ''
                                      ? `${Number(vatRateValue).toLocaleString('sv-SE', { maximumFractionDigits: 2 })}%`
                                      : '-';

                                  const accountFieldKey = `proposals[${globalIndex}].account`;
                                  const accountCandidates = buildHoverCandidates('account', {
                                    source: 'proposals',
                                    extras: [],
                                    index: globalIndex
                                  });
                                  const accountHoverKey = resolveBoxField(boxes, accountCandidates);
                                  const accountHighlightKey =
                                    accountHoverKey || accountCandidates[0] || accountFieldKey;

                                  const amountFieldKey = `proposals[${globalIndex}].${isDebit ? 'debit' : 'credit'}`;
                                  const amountCandidates = buildHoverCandidates(isDebit ? 'debit' : 'credit', {
                                    source: 'proposals',
                                    extras: [],
                                    index: globalIndex
                                  });
                                  const amountHoverKey = resolveBoxField(boxes, amountCandidates);
                                  const amountHighlightKey =
                                    amountHoverKey || amountCandidates[0] || amountFieldKey;

                                  const vatFieldKey = `proposals[${globalIndex}].vat_rate`;
                                  const vatCandidates = buildHoverCandidates('vat_rate', {
                                    source: 'proposals',
                                    extras: [],
                                    index: globalIndex
                                  });
                                  const vatHoverKey = resolveBoxField(boxes, vatCandidates);
                                  const vatHighlightKey = vatHoverKey || vatCandidates[0] || vatFieldKey;

                                  const notesFieldKey = `proposals[${globalIndex}].notes`;
                                  const notesCandidates = buildHoverCandidates('notes', {
                                    source: 'proposals',
                                    extras: [],
                                    index: globalIndex
                                  });
                                  const notesHoverKey = resolveBoxField(boxes, notesCandidates);
                                  const notesHighlightKey =
                                    notesHoverKey || notesCandidates[0] || notesFieldKey;

                                  return (
                                    <div key={`proposal-${globalIndex}`} className="proposal-card-new">
                                      <div className="proposal-line-new">
                                        <div
                                          className={`proposal-cell-new ${matchHighlight(accountHighlightKey)}`}
                                          onMouseEnter={() => setHoverField(accountHighlightKey)}
                                          onMouseLeave={() => setHoverField(null)}
                                        >
                                          <span className="cell-label-new">{isDebit ? 'Debetkonto' : 'Kreditkonto'}</span>
                                          {editing ? (
                                            <input
                                              className="dm-input-new"
                                              value={accountValue ?? ''}
                                              onChange={(event) => updateProposalDraft(globalIndex, 'account', event.target.value)}
                                              disabled={saving}
                                              placeholder="Konto"
                                            />
                                          ) : (
                                            <div className="cell-value-new">{accountValue || '-'}</div>
                                          )}
                                        </div>
                                        <div
                                          className={`proposal-cell-new ${matchHighlight(amountHighlightKey)}`}
                                          onMouseEnter={() => setHoverField(amountHighlightKey)}
                                          onMouseLeave={() => setHoverField(null)}
                                        >
                                          <span className="cell-label-new">Belopp {isDebit ? 'Debet' : 'Kredit'}</span>
                                          {editing ? (
                                            <div className="proposal-amount-inputs-new">
                                              <input
                                                className="dm-input-new"
                                                value={debitValue ?? ''}
                                                onChange={(event) => updateProposalDraft(globalIndex, 'debit', event.target.value)}
                                                disabled={saving}
                                                placeholder="Debet"
                                              />
                                              <input
                                                className="dm-input-new"
                                                value={creditValue ?? ''}
                                                onChange={(event) => updateProposalDraft(globalIndex, 'credit', event.target.value)}
                                                disabled={saving}
                                                placeholder="Kredit"
                                              />
                                            </div>
                                          ) : (
                                            <div className="cell-value-new">{amountDisplay}</div>
                                          )}
                                        </div>
                                        <div
                                          className={`proposal-cell-new ${matchHighlight(vatHighlightKey)}`}
                                          onMouseEnter={() => setHoverField(vatHighlightKey)}
                                          onMouseLeave={() => setHoverField(null)}
                                        >
                                          <span className="cell-label-new">Momssats</span>
                                          {editing ? (
                                            <input
                                              className="dm-input-new"
                                              value={vatRateValue ?? ''}
                                              onChange={(event) => updateProposalDraft(globalIndex, 'vat_rate', event.target.value)}
                                              disabled={saving}
                                              placeholder="Moms %"
                                            />
                                          ) : (
                                            <div className="cell-value-new">{vatRateDisplay}</div>
                                          )}
                                        </div>
                                        <div
                                          className={`proposal-cell-new ${matchHighlight(notesHighlightKey)}`}
                                          onMouseEnter={() => setHoverField(notesHighlightKey)}
                                          onMouseLeave={() => setHoverField(null)}
                                        >
                                          <span className="cell-label-new">Notering</span>
                                          {editing ? (
                                            <input
                                              className="dm-input-new"
                                              value={notesValue ?? ''}
                                              onChange={(event) => updateProposalDraft(globalIndex, 'notes', event.target.value)}
                                              disabled={saving}
                                              placeholder="Notering"
                                            />
                                          ) : (
                                            <div className="cell-value-new">{notesValue || 'Ingen notering'}</div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="modal-footer receipt-modal-footer">
            <div className="footer-hint">Hovra över fält eller bildmarkeringar för att se kopplingarna.</div>
            <div className="modal-footer-actions">
              {editing ? (
                <>
                  <button type="button" className="btn btn-secondary" onClick={handleToggleEdit} disabled={saving}>
                    Avbryt
                  </button>
                  <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
                    <FiSave />
                    {saving ? 'Sparar...' : 'Spara'}
                  </button>
                </>
              ) : (
                <>
                  <button type="button" className="btn btn-secondary" onClick={handleToggleEdit} disabled={saving || loading || !payload}>
                    <FiEdit2 />
                    Redigera
                  </button>
                  <button type="button" className="btn btn-warning" onClick={handleRestartAI} disabled={restarting || saving || loading || !payload} title="Starta om konvertering (kör OCR och AI från början)">
                    <FiRefreshCw />
                    {restarting ? 'Startar om konvertering...' : 'Starta om konvertering'}
                  </button>
                  <button type="button" className="btn btn-danger" onClick={handleDelete} disabled={saving || loading} title="Radera kvitto">
                    <FiTrash2 />
                    Radera
                  </button>
                </>
              )}
              <button type="button" className="btn btn-text" onClick={onClose} disabled={saving}>
                Stäng
              </button>
            </div>
          </div>
        </div>
      </div>
      {imageViewerOpen && baseImageSrc && (
        <div className="receipt-image-viewer-backdrop" role="dialog" aria-label="Förstorad kvittobild" onClick={handleCloseImageViewer}>
          <div className="receipt-image-viewer-dialog" onClick={(event) => event.stopPropagation()}>
            <div className="receipt-image-viewer-toolbar">
              <div className="receipt-image-viewer-zoom">Zoom: {Math.round(imageZoom * 100)}%</div>
              <div className="receipt-image-viewer-toolbar-buttons">
                <button type="button" className="btn btn-text" onClick={handleResetImageZoom}>
                  Återställ zoom
                </button>
                <button type="button" className="btn btn-secondary" onClick={handleCloseImageViewer}>
                  Stäng
                </button>
              </div>
            </div>
            <div className="receipt-image-viewer-canvas" onWheel={handleImageViewerWheel}>
              <img
                src={baseImageSrc}
                alt={`Förstorad vy kvitto ${safeReceiptId || ''}`}
                style={{ transform: `scale(${imageZoom})`, transformOrigin: 'center top' }}
                draggable={false}
              />
            </div>
            <p className="receipt-image-viewer-hint">Tips: Håll ned Ctrl (eller ⌘) och använd mushjulet för att zooma.</p>
          </div>
        </div>
      )}
    </>
  );
}














