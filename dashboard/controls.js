/* A select-only combobox: selection is committed by Enter, Space or a click. */
class AtlasChoice {
  static opened = null;
  constructor(select, {label, kind = 'year', caption = '', labels = {}}) {
    this.select = select;
    this.kind = kind;
    this.labels = labels;
    this.caption = caption;
    this.active = 0;
    this.query = '';
    this.wrapper = document.createElement('div');
    this.wrapper.className = 'atlas-choice';
    select.before(this.wrapper);
    this.wrapper.append(select);
    select.hidden = true;
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');
    this.button = document.createElement('button');
    this.button.type = 'button';
    this.button.id = select.id + '-choice';
    this.button.className = 'choice-trigger';
    this.button.setAttribute('role', 'combobox');
    this.button.setAttribute('aria-label', label);
    this.button.setAttribute('aria-haspopup', 'listbox');
    this.button.setAttribute('aria-expanded', 'false');
    this.button.setAttribute('aria-controls', select.id + '-options');
    this.wrapper.append(this.button);
    document.querySelector(`label[for="${select.id}"]`)?.setAttribute('for', this.button.id);
    this.popup = document.createElement('div');
    this.popup.id = select.id + '-options';
    this.popup.className = 'choice-popup choice-' + kind;
    this.popup.setAttribute('role', 'listbox');
    this.popup.setAttribute('aria-label', label);
    this.popup.hidden = true;
    document.body.append(this.popup);
    this.button.addEventListener('click', () => this.isOpen ? this.close() : this.open());
    this.button.addEventListener('keydown', e => this.keydown(e));
    this.button.addEventListener('blur', () => this.close());
    this.popup.addEventListener('pointerdown', e => e.preventDefault());
    this.popup.addEventListener('click', e => {
      const option = e.target.closest('[data-choice-index]');
      if (option) this.commit(Number(option.dataset.choiceIndex));
    });
    document.addEventListener('pointerdown', e => {
      if (this.isOpen && !this.wrapper.contains(e.target) && !this.popup.contains(e.target)) this.close();
    });
    window.addEventListener('resize', () => this.close());
    window.addEventListener('scroll', e => { if (!this.popup.contains(e.target)) this.close(); }, true);
    this.refresh();
  }
  get isOpen() { return !this.popup.hidden; }
  get items() { return Array.from(this.select.options).filter(o => !o.disabled); }
  text(option) { return this.labels[option.value] || option.text; }
  refresh() {
    this.close();
    const items = this.items;
    const selected = items.find(o => o.value === this.select.value);
    const icon = this.kind === 'year'
      ? '<path d="M6 3v4m12-4v4M4 10h16M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1Z"/>'
      : '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Zm6-3v15m6-12v15"/>';
    this.button.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${icon}</svg><span class="choice-text"><small>${this.caption}</small><strong></strong></span><span class="choice-mark" aria-hidden="true">+</span>`;
    this.button.querySelector('strong').textContent = selected ? selected.text : 'Нет срезов';
    this.button.querySelector('small').hidden = !this.caption;
    this.button.disabled = !items.length;
    this.active = Math.max(0, items.findIndex(o => o.value === this.select.value));
    this.popup.replaceChildren();
    items.forEach((option, index) => {
      const node = document.createElement('div');
      node.id = this.select.id + '-option-' + index;
      node.className = 'choice-option';
      node.setAttribute('role', 'option');
      node.setAttribute('aria-selected', String(option.value === this.select.value));
      node.dataset.choiceIndex = index;
      if (this.kind === 'district' && option.value !== 'all') {
        const badge = document.createElement('span');
        badge.className = 'district-code';
        badge.textContent = option.value;
        const text = document.createElement('span');
        text.textContent = this.text(option);
        node.append(badge, text);
      } else node.textContent = this.text(option);
      this.popup.append(node);
    });
  }
  open() {
    if (this.button.disabled) return;
    AtlasChoice.opened?.close();
    AtlasChoice.opened = this;
    this.active = Math.max(0, this.items.findIndex(o => o.value === this.select.value));
    this.popup.hidden = false;
    this.button.setAttribute('aria-expanded', 'true');
    this.position();
    this.highlight(this.active);
  }
  position() {
    const rect = this.button.getBoundingClientRect();
    const width = Math.min(this.kind === 'district' ? 310 : 256, window.innerWidth - 24);
    this.popup.style.width = width + 'px';
    this.popup.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)) + 'px';
    const availableBelow = window.innerHeight - rect.bottom - 20;
    const height = Math.min(this.popup.scrollHeight + 2, 380);
    const above = availableBelow < height && rect.top > availableBelow;
    this.popup.style.maxHeight = Math.max(100, Math.min(380, above ? rect.top - 20 : availableBelow)) + 'px';
    this.popup.style.top = (above ? Math.max(12, rect.top - Math.min(height, rect.top - 20) - 8) : rect.bottom + 8) + 'px';
  }
  highlight(index) {
    this.active = Math.max(0, Math.min(index, this.items.length - 1));
    const options = this.popup.querySelectorAll('[role="option"]');
    options.forEach((node, i) => node.classList.toggle('choice-active', i === this.active));
    const node = options[this.active];
    if (node) {
      this.button.setAttribute('aria-activedescendant', node.id);
      // Scroll only the popup, so the page and its focus remain stable.
      if (node.offsetTop < this.popup.scrollTop) this.popup.scrollTop = node.offsetTop;
      else if (node.offsetTop + node.offsetHeight > this.popup.scrollTop + this.popup.clientHeight)
        this.popup.scrollTop = node.offsetTop + node.offsetHeight - this.popup.clientHeight;
    }
  }
  close() {
    this.popup.hidden = true;
    this.button.setAttribute('aria-expanded', 'false');
    this.button.removeAttribute('aria-activedescendant');
    if (AtlasChoice.opened === this) AtlasChoice.opened = null;
    this.query = '';
    clearTimeout(this.queryTimer);
  }
  commit(index) {
    const option = this.items[index];
    if (!option) return;
    this.close();
    this.select.value = option.value;
    this.select.dispatchEvent(new Event('change', {bubbles: true}));
    this.refresh();
    this.button.focus({preventScroll: true});
  }
  keydown(e) {
    if (e.key === 'Tab') { this.close(); return; }
    if (e.key === 'Escape') { if (this.isOpen) { e.preventDefault(); this.close(); } return; }
    if (['Enter', ' '].includes(e.key)) {
      e.preventDefault();
      if (this.isOpen) this.commit(this.active); else this.open();
      return;
    }
    const movement = {ArrowDown: 1, ArrowUp: -1, ArrowRight: 1, ArrowLeft: -1};
    if (Object.hasOwn(movement, e.key) || ['Home', 'End'].includes(e.key)) {
      e.preventDefault();
      if (!this.isOpen) { this.open(); if (!['Home', 'End'].includes(e.key)) return; }
      this.highlight(e.key === 'Home' ? 0 : e.key === 'End' ? this.items.length - 1 : this.active + movement[e.key]);
      return;
    }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      if (!this.isOpen) this.open();
      clearTimeout(this.queryTimer);
      this.query += e.key.toLocaleLowerCase('ru');
      this.queryTimer = setTimeout(() => { this.query = ''; }, 700);
      const index = this.items.findIndex(o => [o.value, this.text(o)].some(text => text.toLocaleLowerCase('ru').startsWith(this.query)));
      if (index >= 0) this.highlight(index);
    }
  }
}
const selectionControls = {};
function initSelectionControls() {
  const labels = {ЦФО:'Центральный', СЗФО:'Северо-Западный', ЮФО:'Южный', СКФО:'Северо-Кавказский', ПФО:'Приволжский', УФО:'Уральский', СФО:'Сибирский', ДФО:'Дальневосточный'};
  for (const [id, label, caption, kind] of [['from','Начальный год','Начало','year'],['to','Конечный год','Конец','year'],['district','Федеральный округ','','district'],['anchor','Год рейтинга','','year']])
    selectionControls[id] = new AtlasChoice(document.getElementById(id), {label, caption, kind, labels: kind === 'district' ? labels : {}});
}
