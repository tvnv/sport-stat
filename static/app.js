const currentLabel = () => document.querySelector(".tabs button.active")?.dataset.label || "last";

function statusLabel(status) {
  return ({FINISHED: "FINI", LIVE: "EN COURS", SCHEDULED: "À VENIR", POSTPONED: "REPORTÉ"})[status] || status;
}

function pill(m) {
  return `<span class="status-pill">${statusLabel(m.status)}</span>`;
}

function matchRow(m, positions) {
  const score = (m.home_score !== null && m.away_score !== null)
    ? `${m.home_score}–${m.away_score}`
    : new Date(m.date).toLocaleTimeString("fr-FR", {hour: "2-digit", minute: "2-digit"});
  const hp = positions.get(m.home_team.id) ?? "–";
  const ap = positions.get(m.away_team.id) ?? "–";
  return `<li class="match-row">${pill(m)} <span class="team home">${m.home_team.name} (${hp})</span> <strong>${score}</strong> <span class="team away">${m.away_team.name} (${ap})</span> <span class="meta">${m.date.slice(0, 10)}</span></li>`;
}

function renderBoard(v) {
  const labelMap = { last: "Dernière journée", today: "Aujourd'hui", next: "Prochaine journée" };
  const rows = v.standings_before?.rows || [];
  const positions = new Map(rows.map(r => [r.team_id, r.position]));
  if (!v.matchday) {
    return `<div class="board"><h3>${v.league_name} <small>(${v.country})</small></h3><div class="meta">${labelMap[v.label]} — aucune journée disponible</div></div>`;
  }
  return `
  <div class="board">
    <h3>${v.league_name} <small>(${v.country})</small></h3>
    <div class="meta">${labelMap[v.label]} — Journée ${v.matchday} — ${v.matches.length} matchs</div>
    <ul>${v.matches.map(m => matchRow(m, positions)).join("")}</ul>
  </div>`;
}

async function load() {
  const label = currentLabel();
  const boardsEl = document.getElementById("boards");
  const boardEl = document.getElementById("board");
  const standingsEl = document.getElementById("standings");
  if (boardsEl) {
    const res = await fetch(`/api/dashboard?view=${label}`);
    const data = await res.json();
    const country = document.getElementById("country-filter")?.value || "";
    const views = data.views.filter(v => !country || v.country === country);
    boardsEl.innerHTML = views.map(renderBoard).join("");
  } else {
    const id = window.LEAGUE_ID;
    const suffix = label === "last" ? "last-matchday" : label === "next" ? "next-matchday" : "today";
    const res = await fetch(`/api/competitions/${id}/${suffix}`);
    const v = await res.json();
    boardEl.innerHTML = renderBoard(v);
    standingsEl.innerHTML = v.standings_before.rows.length
      ? `<div class="board"><h3>Classement avant la journée ${v.matchday}</h3><table><tr><th>#</th><th>Équipe</th><th>Pts</th><th>Diff</th><th>Buts</th><th>J/G/N/P</th></tr>${v.standings_before.rows.map(r => `<tr><td>${r.position}</td><td>${r.team_name}</td><td>${r.points}</td><td>${r.goal_diff}</td><td>${r.goals_for}</td><td>${r.played}/${r.won}/${r.drawn}/${r.lost}</td></tr>`).join("")}</table></div>`
      : "";
  }
}

async function init() {
  const filter = document.getElementById("country-filter");
  const nav = document.getElementById("league-nav");
  const res = await fetch("/api/competitions");
  const data = await res.json();
  const competitions = data.competitions;
  if (filter) {
    [...new Set(competitions.map(l => l.country))].forEach(country => {
      const o = document.createElement("option"); o.value = country; o.textContent = country; filter.appendChild(o);
    });
    filter.addEventListener("change", load);
  }
  if (nav) {
    competitions.forEach(l => { const o = document.createElement("option"); o.value = l.id; o.textContent = l.name; if (l.id === window.LEAGUE_ID) o.selected = true; nav.appendChild(o); });
    nav.addEventListener("change", () => { window.location = `/competition/${nav.value}`; });
  }
  document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach(x => x.classList.remove("active"));
    b.classList.add("active"); load();
  }));
  load();
}

init();
