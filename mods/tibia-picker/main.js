// The per-agent outfit picker of the Tibia Agents panel, opened as a dialog by agents-tibia
// with props { agent, name, outfit }. Picks an outfit for that one agent, and the outfit's
// colors, with a preview. Colors belong to the outfit (every agent wearing it shares them).
// Also sets each outfit's vocation: how every agent wearing that outfit attacks.
// Python (tools/recolor.py in the source repo) renders the preview and the outfit's sprites;
// it lives in its own mod so rewriting agents-tibia's sprites doesn't reload this dialog.

import { View, div, image } from "gpui-kit";
import { v_flex, h_flex } from "gpui-base";
import { exec, readTextFile, home, appHome, shared, setShared, closeOverlay, props, theme, checking } from "herdr";
import { OUTFITS, RETRO } from "./outfits.js";
import { REPO, PYTHON } from "./config.js";

const SPRITES = "mods/agents-tibia/sprites";
const PARTS = [["cabeca", "Cabeça"], ["corpo", "Corpo"], ["pernas", "Pernas"], ["pes", "Pés"]];
// The classic colors tibia860.py uses when cores.json says nothing.
const CLASSIC = { cabeca: "#ffaa00", corpo: "#3f3fcc", pernas: "#b46337", pes: "#737373" };
const COLUMNS = 8;
const CELL = { w: 60, h: 62 };
const SWATCH = 15;

// The 133 colors of Tibia's outfit window: 19 hues by 7 rows (OTClient's Outfit::getColor).
function tibiaColor(index) {
  const hues = 19;
  let h = 0, s = 0, i = 0;
  if (index % hues !== 0) {
    h = (index % hues) / 18;
    [s, i] = [[0.25, 1], [0.25, 0.75], [0.5, 0.75], [0.667, 0.75], [1, 1], [1, 0.75], [1, 0.5]][Math.floor(index / hues)];
  } else {
    i = 1 - index / hues / 7;
  }
  let r = i, g = i, b = i;
  if (s > 0) {
    if (h < 1 / 6) { r = i; b = i * (1 - s); g = b + (i - b) * 6 * h; }
    else if (h < 2 / 6) { g = i; b = i * (1 - s); r = g - (i - b) * (6 * h - 1); }
    else if (h < 3 / 6) { g = i; r = i * (1 - s); b = r + (i - r) * (6 * h - 2); }
    else if (h < 4 / 6) { b = i; r = i * (1 - s); g = b - (i - r) * (6 * h - 3); }
    else if (h < 5 / 6) { b = i; g = i * (1 - s); r = g + (i - g) * (6 * h - 4); }
    else { r = i; g = i * (1 - s); b = r - (i - g) * (6 * h - 5); }
  }
  return "#" + [r, g, b].map((c) => Math.trunc(c * 255).toString(16).padStart(2, "0")).join("");
}
const PALETTE = Array.from({ length: 133 }, (_, n) => tibiaColor(n));
// The order agents get outfits in when nobody picked one: any outfits, any number of them.
// agents-tibia's AGENT_OUTFITS is the same default; a saved order lives in shared `tibia.agentOrder`.
const DEFAULT_ORDER = ["128", "130", "133", "134", "129", "132", "131"];
const ALL = [...OUTFITS, ...RETRO];
const LOOKTYPES = new Set(ALL.flatMap(([, male, female]) => [String(male), String(female)]));
const savedOrder = () => {
  const order = shared("tibia.agentOrder");
  const valid = Array.isArray(order) && order.length > 0
    && order.every((o) => LOOKTYPES.has(String(o))) && new Set(order.map(String)).size === order.length;
  return valid ? order.map(String) : [...DEFAULT_ORDER];
};
const RETRO_IDS = new Set(RETRO.flatMap(([, male, female]) => [String(male), String(female)]));
const FEMALE_IDS = new Set(ALL.map(([, , female]) => String(female)));
const nameOf = (id) => {
  const name = ALL.find(([, male, female]) => String(male) === id || String(female) === id)?.[0] ?? id;
  return `${name}${RETRO_IDS.has(id) ? " retrô" : ""}${FEMALE_IDS.has(id) ? " (F)" : ""}`;
};
const sameColors = (a, b) => PARTS.every(([part]) => a?.[part] === b?.[part]);
// The vocations agents-tibia knows (its VOCATIONS), one per outfit in shared
// `tibia.outfitVocations` {looktype: id}. An outfit without one is "Mista": the
// spells every agent cast before vocations.
const VOCATIONS = [["sorcerer", "Sorcerer"], ["druid", "Druid"], ["paladin", "Paladin"], ["knight", "Knight"]];
const VOCATION_IDS = new Set(VOCATIONS.map(([id]) => id));
const vocationLabel = (id) => VOCATIONS.find(([v]) => v === id)?.[1] ?? "Mista";

export default class TibiaPicker extends View {
  init(_props, cx) {
    const p = props() ?? {};
    this.agent = p.agent ?? null;
    this.name = p.name || p.agent || "";
    this.outfit = String(p.outfit ?? "128");
    this.wornAtOpen = this.outfit;
    // Vocations picked here, by looktype (null: Mista), kept until "Salvar alterações"
    // or "Vestir este agente". Several outfits can be changed before saving.
    this.pendingVocations = {};
    this.female = [...OUTFITS, ...RETRO].some(([, , female]) => String(female) === this.outfit);
    this.part = "cabeca";
    // "outfit": this agent's outfit and its colors; "order": the agents' automatic order.
    this.tab = this.agent ? "outfit" : String(p.tab ?? "outfit");
    this.order = savedOrder();
    this.selected = 0;
    this.cores = { todos: {}, outfits: {} };
    this.colors = { ...CLASSIC };
    this.saved = { ...CLASSIC };
    this.preview = null;
    this.rendering = false;
    this.pending = false;
    this.busy = false;
    this.message = "";
    const repo = REPO ?? `${home()}/Documents/herdr-tibia-agents`;
    this.python = PYTHON ?? "python3";
    this.paths = {
      tools: `${repo}/tools`,
      source: `${home()}/Documents/tibia-8.6`,
      repoSprites: `${repo}/mods/agents-tibia/sprites`,
      sprites: `${appHome()}/mods/agents-tibia/sprites`,
      previews: `${appHome()}/tibia-preview`,
    };
    if (checking()) return;
    cx.spawn(async (cx) => {
      try {
        const text = await readTextFile(`${this.paths.source}/cores.json`);
        if (text) this.cores = { todos: {}, outfits: {}, ...JSON.parse(text) };
      } catch (error) {
        this.message = `Não consegui ler cores.json: ${error}`;
      }
      this.loadColors();
      this.requestPreview(cx);
      cx.notify();
    });
  }

  // The colors an outfit has now: its own, else the shared ones, else the classic ones.
  colorsOf(outfit) {
    return { ...CLASSIC, ...this.cores.todos, ...(this.cores.outfits?.[outfit] ?? {}) };
  }

  loadColors() {
    this.colors = this.colorsOf(this.outfit);
    this.saved = { ...this.colors };
  }

  colorArgs() {
    return PARTS.flatMap(([part]) => [`--${part}`, this.colors[part]]);
  }

  // One render at a time; only the latest request matters.
  requestPreview(cx) {
    if (checking()) return;
    if (this.rendering) {
      this.pending = true;
      return;
    }
    this.rendering = true;
    const file = `p${Date.now()}.png`;
    const args = ["-I", "-X", "utf8", `${this.paths.tools}/recolor.py`, "--outfit", this.outfit, ...this.colorArgs(),
      "--preview", `${this.paths.previews}/${file}`];
    cx.spawn(async (cx) => {
      try {
        const result = await exec(this.python, args, { timeout: 30000 });
        if (result.code === 0) this.preview = `tibia-preview/${file}`;
        else this.message = (result.stderr || result.stdout).trim().split("\n").pop();
      } catch (error) {
        this.message = `Prévia falhou: ${error}`;
      }
      this.rendering = false;
      if (this.pending) {
        this.pending = false;
        this.requestPreview(cx);
      }
      cx.notify();
    });
  }

  chooseOutfit(id, cx) {
    this.outfit = id;
    this.loadColors();
    this.message = "";
    this.requestPreview(cx);
    cx.notify();
  }

  chooseColor(hex, cx) {
    this.colors = { ...this.colors, [this.part]: hex };
    this.requestPreview(cx);
    cx.notify();
  }

  // The saved vocation of each outfit, by looktype; null is Mista.
  savedVocation(outfit) {
    const saved = shared("tibia.outfitVocations");
    const id = saved && typeof saved === "object" ? saved[outfit] : null;
    return VOCATION_IDS.has(id) ? id : null;
  }

  // An outfit's vocation as shown: picked here, else saved.
  vocationOf(outfit) {
    return outfit in this.pendingVocations ? this.pendingVocations[outfit] : this.savedVocation(outfit);
  }

  // Outfits whose vocation was picked here and differs from the saved one.
  changedVocations() {
    return Object.keys(this.pendingVocations).filter((o) => this.pendingVocations[o] !== this.savedVocation(o));
  }

  saveVocations() {
    const changed = this.changedVocations();
    if (changed.length) {
      const saved = shared("tibia.outfitVocations");
      const next = saved && typeof saved === "object" ? { ...saved } : {};
      for (const o of changed) {
        if (this.pendingVocations[o]) next[o] = this.pendingVocations[o];
        else delete next[o];
      }
      setShared("tibia.outfitVocations", next);
    }
    this.pendingVocations = {};
  }

  setAgentOutfit(outfit) {
    const chosen = { ...(shared("tibia.agentOutfits") ?? {}) };
    if (outfit) chosen[this.agent] = outfit;
    else delete chosen[this.agent];
    setShared("tibia.agentOutfits", chosen);
  }

  // Opened for an agent and showing an outfit other than the one it wears: offer to dress it.
  wearing() {
    return Boolean(this.agent) && this.outfit !== this.wornAtOpen;
  }

  // Not close(): Herdr calls a view's close() when its overlay goes.
  dismiss() {
    closeOverlay(props()?.overlay);
  }

  // Saves the outfits' vocations and this outfit's colors when they changed; `dress` also
  // puts the outfit on the agent. Saving alone never changes which outfit the agent wears.
  save(cx, dress) {
    if (this.busy) return;
    // First, so a failed color render doesn't lose them.
    this.saveVocations();
    const shared_ = { ...CLASSIC, ...this.cores.todos };
    const own = Boolean(this.cores.outfits?.[this.outfit]);
    let mode = null;
    if (!sameColors(this.colors, this.saved)) mode = sameColors(this.colors, shared_) && own ? "--reset" : "--apply";
    if (!mode) {
      if (dress && this.agent) this.setAgentOutfit(this.outfit);
      this.dismiss();
      return;
    }
    this.busy = true;
    this.message = "Aplicando as cores…";
    cx.notify();
    const args = ["-I", "-X", "utf8", `${this.paths.tools}/recolor.py`, "--outfit", this.outfit, ...this.colorArgs(), mode,
      "--sprites", this.paths.sprites, "--sprites", this.paths.repoSprites];
    cx.spawn(async (cx) => {
      try {
        const result = await exec(this.python, args, { timeout: 60000 });
        if (result.code !== 0) throw new Error((result.stderr || result.stdout).trim().split("\n").pop());
        if (dress && this.agent) this.setAgentOutfit(this.outfit);
        this.dismiss();
      } catch (error) {
        this.busy = false;
        this.message = `Não deu para aplicar: ${error.message ?? error}`;
        cx.notify();
      }
    });
  }

  // Order tab: a grid click adds the outfit after the selected place, or selects it if listed.
  addToOrder(id, cx) {
    const at = this.order.indexOf(id);
    if (at >= 0) {
      this.selected = at;
    } else {
      this.selected = Math.min(this.selected + 1, this.order.length);
      this.order = [...this.order.slice(0, this.selected), id, ...this.order.slice(this.selected)];
    }
    cx.notify();
  }

  moveInOrder(index, by, cx) {
    const to = index + by;
    if (to < 0 || to >= this.order.length) return;
    const order = [...this.order];
    [order[index], order[to]] = [order[to], order[index]];
    this.order = order;
    this.selected = to;
    cx.notify();
  }

  removeFromOrder(index, cx) {
    if (this.order.length <= 1) return;
    this.order = this.order.filter((_, i) => i !== index);
    this.selected = Math.min(this.selected, this.order.length - 1);
    cx.notify();
  }

  render(cx) {
    const t = theme();
    const ordering = this.tab === "order";
    const button = (id, label, onClick, primary = false) => div()
      .id(id)
      .px(12)
      .h(28)
      .flex()
      .items_center()
      .rounded(7)
      .text_size(12)
      .border(1)
      .border_color(primary ? t.accent : t.border)
      .text_color(primary ? t.accent : t.foreground)
      .when(!this.busy, (el) => el.hover((s) => s.bg(t.hover)).on_click(onClick))
      .child(label);
    const toggle = (label, female) => div()
      .id(`sex-${label}`)
      .px(8)
      .py(2)
      .rounded(6)
      .text_size(11)
      .text_color(this.female === female ? t.foreground : t.dim)
      .when(this.female === female, (el) => el.bg(t.hover))
      .hover((s) => s.text_color(t.foreground))
      .on_click((_e, cx) => { this.female = female; cx.notify(); })
      .child(label);
    const tab = (id, label) => div()
      .id(`tab-${id}`)
      .px(10)
      .py(3)
      .rounded(6)
      .text_size(12)
      .text_color(this.tab === id ? t.foreground : t.dim)
      .when(this.tab === id, (el) => el.bg(t.hover))
      .hover((s) => s.text_color(t.foreground))
      .on_click((_e, cx) => { this.tab = id; this.message = ""; cx.notify(); })
      .child(label);
    const cell = ([name, male, female]) => {
      const id = String(this.female ? female : male);
      const place = this.order.indexOf(id);
      const on = ordering ? place >= 0 && place === this.selected : id === this.outfit;
      if (ordering) name = place >= 0 ? `${place + 1}º ${name}` : name;
      return v_flex()
        .id(`outfit-${id}`)
        .w(CELL.w)
        .h(CELL.h)
        .flex_none()
        .items_center()
        .justify_center()
        .gap(1)
        .rounded(7)
        .when(on, (el) => el.bg(t.hover).border(1).border_color(t.accent))
        .hover((s) => s.bg(t.hover))
        .on_click((_e, cx) => (ordering ? this.addToOrder(id, cx) : this.chooseOutfit(id, cx)))
        .child(image(`${SPRITES}/${id}/idle.png`).w(42).h(42).flex_none())
        .child(div().max_w(CELL.w - 4).truncate().text_size(9.5)
          .text_color(on ? t.foreground : ordering && place >= 0 ? t.accent : t.muted).child(name));
    };
    const grid = (list) => {
      const rows = [];
      for (let i = 0; i < list.length; i += COLUMNS) rows.push(list.slice(i, i + COLUMNS));
      return rows.map((row) => h_flex().flex_none().children(row.map(cell)));
    };
    const current = this.colors[this.part];
    const swatches = [];
    for (let row = 0; row < 7; row++) {
      swatches.push(h_flex().gap(2).flex_none().children(PALETTE.slice(row * 19, row * 19 + 19).map((hex, col) => div()
        .id(`color-${row * 19 + col}`)
        .w(SWATCH)
        .h(SWATCH)
        .flex_none()
        .rounded(3)
        .bg(hex)
        .border(hex === current ? 2 : 1)
        .border_color(hex === current ? t.foreground : "#00000066")
        .hover((s) => s.border_color(t.foreground))
        .on_click((_e, cx) => this.chooseColor(hex, cx)))));
    }
    const chosen = this.agent ? (shared("tibia.agentOutfits") ?? {})[this.agent] : null;
    const vocation = this.vocationOf(this.outfit);
    const vocationChoice = (id, label) => div()
      .id(`vocation-${id ?? "auto"}`)
      .px(8)
      .py(2)
      .rounded(6)
      .text_size(11)
      .text_color(vocation === id ? t.foreground : t.dim)
      .when(vocation === id, (el) => el.bg(t.hover))
      .hover((s) => s.text_color(t.foreground))
      .on_click((_e, cx) => {
        this.pendingVocations = { ...this.pendingVocations, [this.outfit]: id };
        cx.notify();
      })
      .child(label);
    const name = nameOf(this.outfit);
    const unsaved = this.changedVocations().length;
    const small = (id, label, onClick, enabled = true) => div()
      .id(id)
      .w(20)
      .h(20)
      .flex()
      .flex_none()
      .items_center()
      .justify_center()
      .rounded(4)
      .text_size(12)
      .text_color(enabled ? t.muted : t.border)
      .when(enabled, (el) => el.hover((s) => s.bg(t.hover).text_color(t.foreground)).on_click(onClick))
      .child(label);
    // The order: one row per place, the selected one where grid clicks insert after.
    const orderList = v_flex()
      .id("order-list")
      .h(318)
      .flex_none()
      .gap(2)
      .overflow_y_scrollbar()
      .children(this.order.map((id, i) => h_flex()
        .id(`order-${i}`)
        .h(30)
        .flex_none()
        .gap(8)
        .px(6)
        .items_center()
        .rounded(6)
        .when(i === this.selected, (el) => el.bg(t.hover).border(1).border_color(t.accent))
        .hover((s) => s.bg(t.hover))
        .on_click((_e, cx) => { this.selected = i; cx.notify(); })
        .child(div().w(30).flex_none().text_size(11).text_color(t.accent).child(`${i + 1}º`))
        .child(image(`${SPRITES}/${id}/idle.png`).w(26).h(26).flex_none())
        .child(div().flex_1().min_w(0).truncate().text_size(12).child(`${nameOf(id)} · ${id} · ${vocationLabel(this.vocationOf(id))}`))
        .child(small(`up-${i}`, "↑", (_e, cx) => this.moveInOrder(i, -1, cx), i > 0))
        .child(small(`down-${i}`, "↓", (_e, cx) => this.moveInOrder(i, 1, cx), i < this.order.length - 1))
        .child(small(`remove-${i}`, "✕", (_e, cx) => this.removeFromOrder(i, cx), this.order.length > 1))));

    return v_flex()
      .size_full()
      .p(14)
      .gap(10)
      .bg(t.popover)
      .text_color(t.foreground)
      .child(h_flex()
        .h(26)
        .flex_none()
        .gap(6)
        .items_center()
        .child(tab("outfit", this.agent ? `Outfit de ${this.name}` : "Outfits e cores"))
        .child(tab("order", "Ordem dos agentes"))
        .child(div().flex_1())
        .child(toggle("Masculino", false))
        .child(toggle("Feminino", true)))
      .child(h_flex()
        .flex_1()
        .min_h(0)
        .gap(18)
        .items_start()
        .child(v_flex()
          .flex_none()
          .children(grid(OUTFITS))
          .child(div().h(20).flex_none().px(4).text_size(11).text_color(t.dim).child("Retrô"))
          .children(grid(RETRO)))
        .when(ordering, (el) => el.child(v_flex()
          .flex_1()
          .min_w(0)
          .gap(6)
          .child(div().text_size(11).text_color(t.dim)
            .child("Clique num outfit para pôr depois do selecionado. Cada agente novo pega o primeiro livre."))
          .child(orderList)))
        .when(!ordering, (el) => el.child(v_flex()
          .flex_1()
          .min_w(0)
          .gap(9)
          .child(h_flex()
            .h(26)
            .flex_none()
            .gap(4)
            .items_center()
            .child(div().flex_1().text_size(11).text_color(t.dim).child("Vocação"))
            .child(vocationChoice(null, "Mista"))
            .children(VOCATIONS.map(([id, label]) => vocationChoice(id, label))))
          .child(h_flex()
            .h(136)
            .flex_none()
            .rounded(8)
            .bg(t.raised)
            .items_center()
            .justify_center()
            .when(Boolean(this.preview), (el) => el.child(image(this.preview).w(256).h(128).flex_none()))
            .when(!this.preview, (el) => el.child(div().text_size(11).text_color(t.dim).child("Gerando a prévia…"))))
          .child(div().text_size(11).text_color(t.dim)
            .child(`${name} (${this.outfit}) · ${vocationLabel(vocation)}${this.rendering ? " · atualizando…" : ""}`))
          .child(h_flex().gap(6).flex_none().children(PARTS.map(([part, label]) => h_flex()
            .id(`part-${part}`)
            .flex_1()
            .h(28)
            .gap(6)
            .px(6)
            .items_center()
            .rounded(6)
            .border(1)
            .border_color(part === this.part ? t.accent : t.border)
            .when(part === this.part, (el) => el.bg(t.hover))
            .hover((s) => s.bg(t.hover))
            .on_click((_e, cx) => { this.part = part; cx.notify(); })
            .child(div().w(14).h(14).flex_none().rounded(3).bg(this.colors[part]).border(1).border_color("#00000066"))
            .child(div().text_size(11).truncate().child(label)))))
          .child(v_flex().gap(2).flex_none().children(swatches))
          .child(div().text_size(10.5).text_color(t.dim)
            .child("As cores e a vocação valem para este outfit em todos os agentes que o usarem.")))))
      .when(ordering, (el) => el.child(h_flex()
        .h(30)
        .flex_none()
        .gap(8)
        .items_center()
        .child(div().flex_1().min_w(0).truncate().text_size(11).text_color(t.dim)
          .child(`${this.order.length} outfits na ordem`))
        .child(button("order-default", "Ordem padrão", (_e, cx) => {
          this.order = [...DEFAULT_ORDER];
          this.selected = 0;
          cx.notify();
        }))
        .child(button("order-cancel", "Cancelar", () => this.dismiss()))
        .child(button("order-save", "Salvar ordem", () => {
          setShared("tibia.agentOrder", this.order);
          this.dismiss();
        }, true))))
      .when(!ordering, (el) => el.child(h_flex()
        .h(30)
        .flex_none()
        .gap(8)
        .items_center()
        .child(div().flex_1().min_w(0).truncate().text_size(11)
          .text_color(!this.message && unsaved ? t.accent : t.dim)
          .child(this.message || (unsaved === 1 ? "Vocação alterada: clique em Salvar alterações."
            : unsaved ? `${unsaved} vocações alteradas: clique em Salvar alterações.` : "")))
        .when(Boolean(this.agent && chosen), (el) => el.child(button("auto", "Automático", (_e, cx) => {
          // The outfit goes automatic; a vocation picked meanwhile is saved, not lost.
          this.saveVocations();
          this.setAgentOutfit(null);
          this.dismiss();
        })))
        .child(button("classic", "Cores padrão", (_e, cx) => {
          this.colors = { ...CLASSIC, ...this.cores.todos };
          this.requestPreview(cx);
          cx.notify();
        }))
        .child(button("cancel", "Cancelar", () => this.dismiss()))
        .child(button("save", this.busy ? "Aplicando…" : "Salvar alterações", (_e, cx) => this.save(cx, false), !this.wearing()))
        .when(this.wearing(), (el) => el.child(button("dress", "Vestir este agente", (_e, cx) => this.save(cx, true), true)))));
  }
}
