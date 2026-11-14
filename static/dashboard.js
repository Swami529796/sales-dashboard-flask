// Fetches /api/summary for the chosen filters and redraws the KPI cards and charts.

const NAVY = "#1f4e78";
const PALETTE = ["#1f4e78", "#4f81bd", "#9db7d5", "#f0a202", "#7a8b99", "#c0504d"];
const form = document.getElementById("filters");
const errorBox = document.getElementById("error");
const charts = {};

// Compact Indian-style amounts: Rs 1.25 Cr, Rs 4.20 L, Rs 9,500
function money(value) {
  if (Math.abs(value) >= 1e7) return "Rs " + (value / 1e7).toFixed(2) + " Cr";
  if (Math.abs(value) >= 1e5) return "Rs " + (value / 1e5).toFixed(2) + " L";
  return "Rs " + Math.round(value).toLocaleString("en-IN");
}

const formatters = {
  revenue: money,
  units: (value) => value.toLocaleString("en-IN"),
  orders: (value) => value.toLocaleString("en-IN"),
  avg_order_value: money,
};

function showKpis(kpis, changes) {
  for (const [key, value] of Object.entries(kpis)) {
    document.getElementById("kpi-" + key).textContent = formatters[key](value);
    const element = document.getElementById("chg-" + key);
    const change = changes[key];
    element.className = "change";
    if (change === null) {
      element.textContent = "No earlier period to compare";
    } else {
      element.textContent = (change >= 0 ? "▲ " : "▼ ") + Math.abs(change * 100).toFixed(1) + "% vs previous period";
      element.classList.add(change >= 0 ? "up" : "down");
    }
  }
}

function draw(id, type, data, options = {}) {
  if (charts[id]) {
    charts[id].data = data;
    charts[id].update();
    return;
  }
  charts[id] = new Chart(document.getElementById(id), {
    type,
    data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: type === "doughnut", position: "bottom" },
        tooltip: { callbacks: { label: (item) => " " + money(item.raw) } },
      },
      ...options,
    },
  });
}

const moneyAxis = { ticks: { callback: (value) => money(value) }, beginAtZero: true };

function showCharts(summary) {
  draw("monthly", "line", {
    labels: summary.monthly.labels,
    datasets: [{ data: summary.monthly.values, borderColor: NAVY, backgroundColor: "rgba(31,78,120,0.12)", fill: true, tension: 0.25, pointRadius: 3 }],
  }, { scales: { y: moneyAxis } });

  draw("category", "doughnut", {
    labels: summary.by_category.labels,
    datasets: [{ data: summary.by_category.values, backgroundColor: PALETTE }],
  });

  draw("region", "bar", {
    labels: summary.by_region.labels,
    datasets: [{ data: summary.by_region.values, backgroundColor: NAVY, borderRadius: 4 }],
  }, { scales: { y: moneyAxis } });

  draw("products", "bar", {
    labels: summary.top_products.labels,
    datasets: [{ data: summary.top_products.values, backgroundColor: "#4f81bd", borderRadius: 4 }],
  }, { indexAxis: "y", scales: { x: { ...moneyAxis, ticks: { ...moneyAxis.ticks, maxTicksLimit: 4 } } } });
}

async function refresh() {
  const query = new URLSearchParams(new FormData(form));
  try {
    const response = await fetch("/api/summary?" + query);
    const summary = await response.json();
    if (!response.ok) throw new Error(summary.error || "The data could not be loaded.");
    errorBox.hidden = true;
    document.getElementById("shown").textContent = summary.rows.toLocaleString("en-IN") + " shown";
    showKpis(summary.kpis, summary.changes);
    showCharts(summary);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  }
}

form.addEventListener("change", refresh);
form.addEventListener("reset", () => setTimeout(refresh)); // wait for the fields to reset first
refresh();
