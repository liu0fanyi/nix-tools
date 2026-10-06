/* Shared browser/Node ingredient matching. Only ingredient terms are searched. */
(function (root) {
  'use strict';
  const normalize = value => String(value).normalize('NFKC').trim().toLowerCase();
  const tokens = query => normalize(query).split(/[\s,，、]+/u).filter(Boolean);
  const prepare = records => records.map(record => ({
    ...record,
    terms: record.ingredients.map(item => ({
      ...item,
      key: normalize(item.name),
      keys: [...new Set([item.name, ...(item.search_terms || [])].map(normalize))]
    }))
  }));
  const itemMatches = (item, word) => item.keys.some(key => key.includes(word));
  const matches = (record, query, includeOptional = true) => tokens(query).every(word =>
    record.terms.some(item => (includeOptional || item.role !== 'optional') && itemMatches(item, word)));
  const api = {normalize, tokens, prepare, itemMatches, matches};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RecipeIngredientSearch = api;
})(globalThis);
