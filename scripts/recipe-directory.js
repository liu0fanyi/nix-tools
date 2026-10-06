(() => {
  const {tokens, prepare, matches, itemMatches} = RecipeIngredientSearch;
  let records = prepare(JSON.parse(document.getElementById('recipe-data').textContent));
  const query = document.getElementById('query');
  const optional = document.getElementById('optional');
  const cards = document.getElementById('cards');
  const summary = document.getElementById('summary');
  const empty = document.getElementById('empty');
  const previous = document.getElementById('previous');
  const next = document.getElementById('next');
  const pageLabel = document.getElementById('page-label');
  const pageSize = 24;
  const saved = new URLSearchParams(location.hash.slice(1));
  query.value = saved.get('q') || '';
  optional.checked = saved.get('optional') !== '0';
  let page = Math.max(1, Number(saved.get('page')) || 1);
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function render() {
    const found = records.filter(record => matches(record, query.value, optional.checked));
    const pages = Math.max(1, Math.ceil(found.length / pageSize));
    page = Math.min(Math.max(page, 1), pages);
    cards.replaceChildren();
    const words = tokens(query.value);
    for (const record of found.slice((page - 1) * pageSize, page * pageSize)) {
      const card = element('a', 'card');
      card.href = record.page;
      if (record.thumbnail) {
        const image = element('img');
        image.src = record.thumbnail;
        image.alt = record.title + '操作画面';
        image.loading = 'lazy';
        image.width = 480;
        image.height = 270;
        card.append(image);
      }
      const body = element('div', 'card-body');
      body.append(element('h2', '', record.title));
      const labels = element('div', 'ingredients');
      const unique = [...new Map(record.terms.filter(item => optional.checked || item.role !== 'optional').map(item => [item.name, item])).values()];
      const matching = unique.filter(item => words.some(word => itemMatches(item, word)));
      const listed = [...matching, ...unique.filter(item => !matching.includes(item))].slice(0, 8);
      for (const item of listed) {
        const label = element('span', matching.includes(item) ? 'ingredient matched' : 'ingredient', item.name + (item.role === 'optional' ? ' · 可选' : ''));
        labels.append(label);
      }
      if (unique.length > listed.length) labels.append(element('span', 'more', '+' + (unique.length - listed.length)));
      body.append(labels, element('p', 'review', 'AI试稿 · ' + record.issues + '项待核对'));
      card.append(body);
      cards.append(card);
    }
    summary.textContent = query.value.trim() ? '找到 ' + found.length + ' 道菜谱 · 匹配食材清单' : '共 ' + records.length + ' 道菜谱';
    empty.hidden = found.length !== 0;
    previous.disabled = page <= 1;
    next.disabled = page >= pages;
    pageLabel.textContent = page + ' / ' + pages;
    const params = new URLSearchParams({q: query.value, optional: optional.checked ? '1' : '0', page: String(page)});
    history.replaceState(null, '', '#' + params.toString());
    return found.length;
  }
  let timer;
  query.addEventListener('input', () => {clearTimeout(timer); timer = setTimeout(() => {page = 1; render();}, 120);});
  optional.addEventListener('change', () => {page = 1; render();});
  document.getElementById('clear').addEventListener('click', () => {clearTimeout(timer); query.value = ''; page = 1; render(); query.focus();});
  previous.addEventListener('click', () => {page--; render();});
  next.addEventListener('click', () => {page++; render();});
  document.querySelectorAll('[data-search]').forEach(button => button.addEventListener('click', () => {query.value = button.dataset.search; page = 1; render();}));
  window.recipeSearch = {prepare, matches, render, replaceRecords: data => {records = prepare(data); page = 1; return render();}};
  render();
})();
