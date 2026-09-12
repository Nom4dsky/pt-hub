/* Exercise Database — vanilla JS frontend. No framework, no build step. */

// ---------- shared state ----------
let movementPatterns = [];
let muscles = [];
let equipmentList = [];

let editingExerciseId = null;      // null => create mode
let currentMuscleLinks = [];       // [{muscle_id, role, _name?}]
let currentEquipmentLinks = [];    // [{equipment_id, is_required, _name?}]
let variantSelectedId = null;
let variantOptionsCache = null;

let currentLookupTab = "movement-patterns";
const LOOKUP_CONFIG = {
  "movement-patterns": { path: "/api/movement-patterns", label: "movement pattern" },
  muscles: { path: "/api/muscles", label: "muscle" },
  equipment: { path: "/api/equipment", label: "equipment" },
};

// ---------- API helper ----------
async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!res.ok) {
    throw new Error(data && data.detail ? formatDetail(data.detail) : `Request failed (${res.status})`);
  }
  return data;
}

function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI 422 validation error shape
    return detail.map((d) => `${(d.loc || []).slice(-1)[0] || "field"}: ${d.msg}`).join("; ");
  }
  return JSON.stringify(detail);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// Display-only: movement_pattern values are stored snake_case
// (e.g. "pull_horizontal") — never reformatted in the DB or API, just
// rendered readable wherever a movement pattern name shows up in the UI.
function formatMovementPattern(name) {
  return (name ?? "")
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function showError(id, message) {
  const el = document.getElementById(id);
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError(id) {
  const el = document.getElementById(id);
  el.textContent = "";
  el.classList.add("hidden");
}

// ---------- navigation ----------
function showView(view) {
  document.querySelectorAll(".view").forEach((el) => el.classList.add("hidden"));
  document.getElementById("view-" + view).classList.remove("hidden");
  document.querySelectorAll("#main-nav .tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
}

document.querySelectorAll("#main-nav .tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const view = btn.dataset.view;
    if (view === "form") {
      openAddForm(); // top-nav entry to the form always starts a fresh add
    } else {
      showView(view);
      if (view === "lookups") loadLookupTab(currentLookupTab);
    }
  });
});

// ---------- browse: filter dropdowns + table ----------
function fillSelect(id, items, hasAnyOption, formatLabel = (name) => name) {
  const sel = document.getElementById(id);
  const startIdx = hasAnyOption ? 1 : 0;
  while (sel.options.length > startIdx) sel.remove(startIdx);
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = formatLabel(item.name);
    sel.appendChild(opt);
  }
}

async function loadLookupCaches() {
  [movementPatterns, muscles, equipmentList] = await Promise.all([
    api("GET", "/api/movement-patterns"),
    api("GET", "/api/muscles"),
    api("GET", "/api/equipment"),
  ]);
  fillSelect("f-movement-pattern", movementPatterns, true, formatMovementPattern);
  fillSelect("f-muscle", muscles, true);
  fillSelect("f-equipment", equipmentList, true);
  fillSelect("ex-movement-pattern", movementPatterns, false, formatMovementPattern);
  fillSelect("muscle-picker", muscles, false);
  fillSelect("equipment-picker", equipmentList, false);
}

async function applyFilters() {
  const params = new URLSearchParams();
  const mp = document.getElementById("f-movement-pattern").value;
  const mu = document.getElementById("f-muscle").value;
  const eq = document.getElementById("f-equipment").value;
  const et = document.getElementById("f-exercise-type").value;
  const co = document.getElementById("f-compound-or-isolation").value;
  const dmin = document.getElementById("f-difficulty-min").value;
  const dmax = document.getElementById("f-difficulty-max").value;
  const search = document.getElementById("f-search").value.trim();

  if (mp) params.set("movement_pattern_id", mp);
  if (mu) params.set("muscle_id", mu);
  if (eq) params.set("equipment_id", eq);
  if (et) params.set("exercise_type", et);
  if (co) params.set("compound_or_isolation", co);
  if (dmin) params.set("difficulty_min", dmin);
  if (dmax) params.set("difficulty_max", dmax);
  if (search) params.set("search", search);

  clearError("error-banner");
  try {
    const list = await api("GET", "/api/exercises?" + params.toString());
    renderExerciseTable(list);
  } catch (e) {
    showError("error-banner", e.message);
  }
}

function renderExerciseTable(list) {
  const tbody = document.getElementById("exercise-table-body");
  tbody.innerHTML = "";
  document.getElementById("result-count").textContent =
    `${list.length} exercise${list.length === 1 ? "" : "s"}`;

  if (list.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="5" class="muted">No exercises match these filters.</td>`;
    tbody.appendChild(tr);
    return;
  }

  for (const ex of list) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(ex.name)}</td>
      <td>${escapeHtml(formatMovementPattern(ex.movement_pattern_name))}</td>
      <td>${escapeHtml(ex.primary_muscle || "—")}</td>
      <td>${ex.difficulty}</td>
      <td>${escapeHtml(ex.exercise_type)}</td>
    `;
    tr.addEventListener("click", () => openEditForm(ex.id));
    tbody.appendChild(tr);
  }
}

document.getElementById("f-apply").addEventListener("click", applyFilters);
document.getElementById("f-clear").addEventListener("click", () => {
  ["f-movement-pattern", "f-muscle", "f-equipment", "f-exercise-type", "f-compound-or-isolation"].forEach(
    (id) => (document.getElementById(id).value = "")
  );
  ["f-difficulty-min", "f-difficulty-max", "f-search"].forEach((id) => (document.getElementById(id).value = ""));
  applyFilters();
});

document.getElementById("add-exercise-btn").addEventListener("click", openAddForm);

// ---------- add/edit form ----------
function resetForm() {
  editingExerciseId = null;
  document.getElementById("ex-id").value = "";
  document.getElementById("form-title").textContent = "Add Exercise";
  document.getElementById("exercise-form").reset();
  currentMuscleLinks = [];
  currentEquipmentLinks = [];
  renderMuscleChips();
  renderEquipmentChips();
  clearVariantSelection();
  document.getElementById("delete-exercise-btn").classList.add("hidden");
  clearError("form-error");
}

function openAddForm() {
  resetForm();
  showView("form");
}

async function openEditForm(id) {
  clearError("error-banner");
  try {
    const detail = await api("GET", `/api/exercises/${id}`);
    resetForm();
    editingExerciseId = id;

    document.getElementById("ex-id").value = id;
    document.getElementById("form-title").textContent = "Edit Exercise";
    document.getElementById("ex-name").value = detail.name;
    document.getElementById("ex-movement-pattern").value = detail.movement_pattern_id;
    document.getElementById("ex-exercise-type").value = detail.exercise_type;
    document.querySelector(`input[name="ex-compound"][value="${detail.compound_or_isolation}"]`).checked = true;
    document.getElementById("ex-difficulty").value = detail.difficulty;
    document.getElementById("ex-unilateral").checked = detail.unilateral;
    document.getElementById("ex-tracking-type").value = detail.tracking_type;
    document.getElementById("ex-contraindications").value = detail.contraindications || "";
    document.getElementById("ex-cue-notes").value = detail.cue_notes || "";
    document.getElementById("ex-video-url").value = detail.video_url || "";

    currentMuscleLinks = detail.muscles.map((m) => ({ muscle_id: m.muscle_id, role: m.role, _name: m.muscle_name }));
    currentEquipmentLinks = detail.equipment.map((e) => ({
      equipment_id: e.equipment_id,
      is_required: e.is_required,
      _name: e.equipment_name,
    }));
    renderMuscleChips();
    renderEquipmentChips();

    if (detail.variant_of) {
      setVariantSelection(detail.variant_of, detail.variant_of_name);
    }

    document.getElementById("delete-exercise-btn").classList.remove("hidden");
    showView("form");
  } catch (e) {
    showError("error-banner", e.message);
  }
}

// -- muscle chips --
function renderMuscleChips() {
  const ul = document.getElementById("muscle-chip-list");
  ul.innerHTML = "";
  currentMuscleLinks.forEach((link, idx) => {
    const name = link._name || (muscles.find((m) => m.id === link.muscle_id) || {}).name || `#${link.muscle_id}`;
    const li = document.createElement("li");
    li.className = "chip";
    const span = document.createElement("span");
    span.textContent = `${name} — ${link.role}`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "Remove");
    btn.addEventListener("click", () => {
      currentMuscleLinks.splice(idx, 1);
      renderMuscleChips();
    });
    li.appendChild(span);
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

document.getElementById("muscle-add-btn").addEventListener("click", () => {
  const muscleId = parseInt(document.getElementById("muscle-picker").value, 10);
  const role = document.getElementById("muscle-role-picker").value;
  if (!muscleId) return;
  if (currentMuscleLinks.some((l) => l.muscle_id === muscleId && l.role === role)) {
    showError("form-error", "That muscle + role is already added.");
    return;
  }
  clearError("form-error");
  currentMuscleLinks.push({ muscle_id: muscleId, role });
  renderMuscleChips();
});

// -- equipment chips --
function renderEquipmentChips() {
  const ul = document.getElementById("equipment-chip-list");
  ul.innerHTML = "";
  currentEquipmentLinks.forEach((link, idx) => {
    const name =
      link._name || (equipmentList.find((e) => e.id === link.equipment_id) || {}).name || `#${link.equipment_id}`;
    const li = document.createElement("li");
    li.className = "chip";
    const span = document.createElement("span");
    span.textContent = `${name} — ${link.is_required ? "required" : "optional"}`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "Remove");
    btn.addEventListener("click", () => {
      currentEquipmentLinks.splice(idx, 1);
      renderEquipmentChips();
    });
    li.appendChild(span);
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

document.getElementById("equipment-add-btn").addEventListener("click", () => {
  const equipmentId = parseInt(document.getElementById("equipment-picker").value, 10);
  const isRequired = document.getElementById("equipment-required-picker").checked;
  if (!equipmentId) return;
  if (currentEquipmentLinks.some((l) => l.equipment_id === equipmentId)) {
    showError("form-error", "That equipment is already added.");
    return;
  }
  clearError("form-error");
  currentEquipmentLinks.push({ equipment_id: equipmentId, is_required: isRequired });
  renderEquipmentChips();
});

// -- variant-of searchable autocomplete (custom, not <datalist> — iOS Safari support for datalist is unreliable) --
const variantSearchInput = document.getElementById("ex-variant-search");
const variantList = document.getElementById("variant-autocomplete-list");

async function ensureVariantOptions() {
  const excludeParam = editingExerciseId ? `?exclude_id=${editingExerciseId}` : "";
  variantOptionsCache = await api("GET", `/api/exercises/options${excludeParam}`);
}

function renderVariantOptions(query) {
  if (!variantOptionsCache) {
    variantList.classList.add("hidden");
    return;
  }
  const q = query.trim().toLowerCase();
  const matches = (q ? variantOptionsCache.filter((o) => o.name.toLowerCase().includes(q)) : variantOptionsCache).slice(
    0,
    30
  );
  variantList.innerHTML = "";
  if (matches.length === 0) {
    variantList.classList.add("hidden");
    return;
  }
  matches.forEach((opt) => {
    const div = document.createElement("div");
    div.className = "autocomplete-item";
    div.textContent = opt.name;
    div.addEventListener("click", () => {
      setVariantSelection(opt.id, opt.name);
      variantList.classList.add("hidden");
      variantSearchInput.value = "";
    });
    variantList.appendChild(div);
  });
  variantList.classList.remove("hidden");
}

variantSearchInput.addEventListener("focus", async () => {
  if (!variantOptionsCache) await ensureVariantOptions();
  renderVariantOptions(variantSearchInput.value);
});
variantSearchInput.addEventListener("input", () => renderVariantOptions(variantSearchInput.value));
document.addEventListener("click", (e) => {
  if (!document.getElementById("variant-autocomplete").contains(e.target)) {
    variantList.classList.add("hidden");
  }
});

function setVariantSelection(id, name) {
  variantSelectedId = id;
  document.getElementById("ex-variant-of").value = id;
  document.getElementById("variant-selected-name").textContent = name;
  document.getElementById("variant-selected").classList.remove("hidden");
}

function clearVariantSelection() {
  variantSelectedId = null;
  document.getElementById("ex-variant-of").value = "";
  document.getElementById("variant-selected").classList.add("hidden");
  variantSearchInput.value = "";
  variantOptionsCache = null; // exclude_id differs between add/edit — refetch next time it's opened
}

document.getElementById("variant-clear-btn").addEventListener("click", clearVariantSelection);

// -- save / delete --
document.getElementById("exercise-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError("form-error");

  const name = document.getElementById("ex-name").value.trim();
  const movementPatternId = parseInt(document.getElementById("ex-movement-pattern").value, 10);
  const difficulty = parseInt(document.getElementById("ex-difficulty").value, 10);
  const compoundRadio = document.querySelector('input[name="ex-compound"]:checked');

  // Client-side checks mirroring the DB's CHECK constraints — enum fields
  // are covered just by using <select>/<radio> with only valid options,
  // so what's left to check by hand is presence and the numeric range.
  if (!name) return showError("form-error", "Name is required.");
  if (!movementPatternId) return showError("form-error", "Movement pattern is required.");
  if (!(difficulty >= 1 && difficulty <= 6)) return showError("form-error", "Difficulty must be between 1 and 6.");
  if (!compoundRadio) return showError("form-error", "Choose compound or isolation.");

  const payload = {
    name,
    movement_pattern_id: movementPatternId,
    exercise_type: document.getElementById("ex-exercise-type").value,
    difficulty,
    unilateral: document.getElementById("ex-unilateral").checked,
    compound_or_isolation: compoundRadio.value,
    tracking_type: document.getElementById("ex-tracking-type").value,
    contraindications: document.getElementById("ex-contraindications").value.trim() || null,
    cue_notes: document.getElementById("ex-cue-notes").value.trim() || null,
    video_url: document.getElementById("ex-video-url").value.trim() || null,
    variant_of: variantSelectedId || null,
    muscles: currentMuscleLinks.map((l) => ({ muscle_id: l.muscle_id, role: l.role })),
    equipment: currentEquipmentLinks.map((l) => ({ equipment_id: l.equipment_id, is_required: l.is_required })),
  };

  try {
    if (editingExerciseId) {
      await api("PUT", `/api/exercises/${editingExerciseId}`, payload);
    } else {
      await api("POST", "/api/exercises", payload);
    }
    showView("browse");
    applyFilters();
  } catch (err) {
    showError("form-error", err.message);
  }
});

document.getElementById("form-cancel").addEventListener("click", () => showView("browse"));

document.getElementById("delete-exercise-btn").addEventListener("click", async () => {
  if (!editingExerciseId) return;
  if (!confirm("Delete this exercise? This cannot be undone.")) return;
  try {
    await api("DELETE", `/api/exercises/${editingExerciseId}`);
    showView("browse");
    applyFilters();
  } catch (err) {
    showError("form-error", err.message);
  }
});

// ---------- manage lookups ----------
document.querySelectorAll("#lookup-nav .tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    currentLookupTab = btn.dataset.lookup;
    document.querySelectorAll("#lookup-nav .tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
    document.getElementById("lookup-new-name").value = "";
    loadLookupTab(currentLookupTab);
  });
});

async function loadLookupTab(tab) {
  clearError("lookup-error");
  const cfg = LOOKUP_CONFIG[tab];
  try {
    const items = await api("GET", cfg.path);
    renderLookupList(items, cfg);
  } catch (e) {
    showError("lookup-error", e.message);
  }
}

function renderLookupList(items, cfg) {
  const ul = document.getElementById("lookup-list");
  ul.innerHTML = "";

  if (items.length === 0) {
    const li = document.createElement("li");
    li.className = "lookup-item";
    li.innerHTML = `<span class="muted">No ${cfg.label} entries yet.</span>`;
    ul.appendChild(li);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "lookup-item";

    const nameSpan = document.createElement("span");
    nameSpan.className = "lookup-name";
    nameSpan.textContent = item.name;

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-ghost";
    editBtn.textContent = "Edit";

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-danger";
    deleteBtn.textContent = "Delete";

    li.appendChild(nameSpan);
    li.appendChild(editBtn);
    li.appendChild(deleteBtn);
    ul.appendChild(li);

    editBtn.addEventListener("click", () => {
      li.innerHTML = "";

      const input = document.createElement("input");
      input.type = "text";
      input.value = item.name;

      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.className = "btn btn-primary";
      saveBtn.textContent = "Save";

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "btn btn-ghost";
      cancelBtn.textContent = "Cancel";

      li.appendChild(input);
      li.appendChild(saveBtn);
      li.appendChild(cancelBtn);

      cancelBtn.addEventListener("click", () => loadLookupTab(currentLookupTab));
      saveBtn.addEventListener("click", async () => {
        const newName = input.value.trim();
        if (!newName) return showError("lookup-error", "Name is required.");
        try {
          await api("PUT", `${cfg.path}/${item.id}`, { name: newName });
          loadLookupTab(currentLookupTab);
        } catch (e) {
          showError("lookup-error", e.message);
        }
      });
    });

    deleteBtn.addEventListener("click", async () => {
      if (!confirm(`Delete "${item.name}"?`)) return;
      try {
        await api("DELETE", `${cfg.path}/${item.id}`);
        loadLookupTab(currentLookupTab);
      } catch (e) {
        showError("lookup-error", e.message);
      }
    });
  });
}

document.getElementById("lookup-add-btn").addEventListener("click", async () => {
  const input = document.getElementById("lookup-new-name");
  const name = input.value.trim();
  if (!name) return showError("lookup-error", "Name is required.");
  const cfg = LOOKUP_CONFIG[currentLookupTab];
  try {
    await api("POST", cfg.path, { name });
    input.value = "";
    loadLookupTab(currentLookupTab);
  } catch (e) {
    showError("lookup-error", e.message);
  }
});

// ---------- init ----------
(async function init() {
  try {
    await loadLookupCaches();
    await applyFilters();
  } catch (e) {
    showError("error-banner", e.message);
  }
})();
