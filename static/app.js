const leagues = (window.LEAGUES || []);
const currentLabel = () => document.querySelector(".tabs button.active")?.dataset.label || "last";

function pill(m) {
  return `<span class="status-pill">${m.status}</span>`;
}

function matchRow(m) {
  const s = (m.home_score !== null && m.away_score !== null) ? `${m.home_score} - ${m.away_score}` : "–";
  return `<li>${pill(m)} <span>${m.home_team.name} vs ${m.away_team.name}</span> <span>${s}</span> <span class="meta">${m.date.slice(0, 16).replace("T", " ")}</span></li>`;
}

function renderBoard(v, standingsRows) {
  const labelMap = { last: "Dernière journée", today: "Aujourd'hui", next: "Prochaine journée" };
  const s = standingsRows ? standingsRows.filter(r => r.played > 0) : [];
  const table = s.length ? `
    <details open><summary>Classement avant la journée ${v.matchday}</summary>
    <table><tr><th>#</th><th>Équipe</th><th>Pts</th><th>Diff</th><th>Buts</th></tr>
    ${s.map(r => `<tr><td>${r.position}</td><td>${r.team_name}</td><td>${r.points}</td><td>${r.goal_diff}</td><td>${r.goals_for}</td></tr>`).join("")}
    </table></details>` : "";
  return `
  <div class="board">
    <h3>${v.league_name} <small>(${v.country})</small></h3>
    <div class="meta">${labelMap[v.label]} — Journée ${v.matchday} — ${v.matches.length} matchs</div>
    <ul>${v.matches.map(matchRow).join("")}</ul>
    ${table}
  </div>`;
}

async function load() {
  const label = currentLabel();
  const boardsEl = document.getElementById("boards");
  const boardEl = document.getElementById("board");
  const standingsEl = document.getElementById("standings");
  if (boardsEl) {
    const res = await fetch(`/api/dashboard?label=${label}`);
    const data = await res.json();
    const leagueFilter = document.getElementById("league-filter").value;
    const views = data.views.filter(v => !leagueFilter || v.league_id === leagueFilter);
    boardsEl.innerHTML = views.map(v => renderBoard(v, v.standings_before.rows)).join("");
  } else {
    const id = window.LEAGUE_ID;
    const res = await fetch(`/api/competition/${id}?label=${label}`);
    const v = await res.json();
    boardEl.innerHTML = renderBoard(v, null);
    standingsEl.innerHTML = v.standings_before.rows.length
      ? `<div class="board"><h3>Classement avant la journée ${v.matchday}</h3><table><tr><th>#</th><th>Équipe</th><th>Pts</th><th>Diff</th><th>Buts</th><th>J/G/N/P</th></tr>${v.standings_before.rows.map(r => `<tr><td>${r.position}</td><td>${r.team_name}</td><td>${r.points}</td><td>${r.goal_diff}</td><td>${r.goals_for}</td><td>${r.played}/${r.won}/${r.drawn}/${r.lost}</td></tr>`).join("")}</table></div>`
      : "";
  }
}

async function init() {
  const filter = document.getElementById("league-filter");
  const nav = document.getElementById("league-nav");
  if (filter) {
    const res = await fetch("/api/leagues"); const data = await res.json();
    data.leagues.forEach(l => { const o = document.createElement("option"); o.value = l.id; o.textContent = `${l.country} — ${l.name}`; filter.appendChild(o); });
  }
  if (nav) {
    const res = await fetch("/api/leagues"); const data = await res.json();
    data.leagues.forEach(l => { const o = document.createElement("option"); o.value = l.id; o.textContent = l.name; if (l.id === window.LEAGUE_ID) o.selected = true; nav.appendChild(o); });
    nav.addEventListener("change", () => { window.location = `/competition/${nav.value}`; });
  }
  document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach(x => x.classList.remove("active"));
    b.classList.add("active"); load();
  }));
  load();
}

init();