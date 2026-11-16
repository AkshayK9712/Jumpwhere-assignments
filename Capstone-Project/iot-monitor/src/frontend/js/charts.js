// D3 charts. Colours come from CSS classes (see styles.css), so dark mode works automatically.
// Text is always set with .text(), never as HTML.
const note = (text) => Object.assign(document.createElement("p"), { className: "chart-empty", textContent: text });

export function renderLineChart(host, d3, { points, unit = "", thresholds = null, from = null, to = null }) {
  host.replaceChildren();
  if (!points.length) {
    host.append(note("No readings in this period."));
    return;
  }
  const data = points.map((p) => ({ t: new Date(p.bucket), avg: p.avg, min: p.min, max: p.max, count: p.count }));
  const width = Math.max(300, host.clientWidth || 640);
  const height = width < 480 ? 240 : 320;
  const m = { top: 12, right: 16, bottom: 28, left: 52 };
  const suffix = unit ? ` ${unit}` : "";

  let [t0, t1] = [from ?? d3.min(data, (d) => d.t), to ?? d3.max(data, (d) => d.t)];
  if (+t0 === +t1) [t0, t1] = [new Date(+t0 - 30 * 60e3), new Date(+t1 + 30 * 60e3)];
  const x = d3.scaleTime().domain([t0, t1]).range([m.left, width - m.right]);

  const extremes = data.flatMap((d) => [d.min, d.max]);
  for (const key of ["min", "max"]) if (thresholds?.[key] != null) extremes.push(thresholds[key]);
  const lo = d3.min(extremes);
  const hi = d3.max(extremes);
  const pad = (hi - lo) * 0.08 || 1;
  const y = d3.scaleLinear().domain([lo - pad, hi + pad]).nice().range([height - m.bottom, m.top]);

  const svg = d3.select(host).append("svg").attr("class", "chart").attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img").attr("aria-label", `Line chart of ${data.length} data points${unit ? ` in ${unit}` : ""}`);

  svg.append("g").attr("class", "grid").attr("transform", `translate(${m.left},0)`)
    .call(d3.axisLeft(y).ticks(6).tickSize(-(width - m.left - m.right)).tickFormat(""));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${height - m.bottom})`)
    .call(d3.axisBottom(x).ticks(width < 500 ? 4 : 7).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.left},0)`).call(d3.axisLeft(y).ticks(6));

  svg.append("path").datum(data).attr("class", "chart-band")
    .attr("d", d3.area().x((d) => x(d.t)).y0((d) => y(d.min)).y1((d) => y(d.max)));
  svg.append("path").datum(data).attr("class", "chart-line")
    .attr("d", d3.line().x((d) => x(d.t)).y((d) => y(d.avg)));

  for (const key of ["min", "max"]) {
    const value = thresholds?.[key];
    if (value == null) continue;
    svg.append("line").attr("class", "chart-threshold").attr("x1", m.left).attr("x2", width - m.right).attr("y1", y(value)).attr("y2", y(value));
    svg.append("text").attr("class", "chart-threshold-label").attr("x", width - m.right - 4).attr("y", y(value) - 4)
      .attr("text-anchor", "end").text(`${key} ${value}${suffix}`);
  }

  const isAlert = (d) => (thresholds?.max != null && d.max > thresholds.max) || (thresholds?.min != null && d.min < thresholds.min);
  if (data.length <= 80) {
    svg.selectAll("circle.chart-dot").data(data).join("circle")
      .attr("class", (d) => `chart-dot${isAlert(d) ? " alert" : ""}`).attr("cx", (d) => x(d.t)).attr("cy", (d) => y(d.avg)).attr("r", 2.8);
  }

  // hover / touch tooltip
  const tip = d3.select(host).append("div").attr("class", "chart-tip").attr("hidden", true);
  const focus = svg.append("circle").attr("class", "chart-focus").attr("r", 5).attr("visibility", "hidden");
  const bisect = d3.bisector((d) => d.t).center;
  const fmt = d3.timeFormat("%b %d, %H:%M");
  svg.append("rect").attr("class", "chart-overlay").attr("x", m.left).attr("y", m.top)
    .attr("width", width - m.left - m.right).attr("height", height - m.top - m.bottom)
    .on("pointermove", (event) => {
      const d = data[bisect(data, x.invert(d3.pointer(event)[0]))];
      focus.attr("cx", x(d.t)).attr("cy", y(d.avg)).attr("visibility", "visible");
      tip.attr("hidden", null).style("left", `${(x(d.t) / width) * host.clientWidth}px`).style("top", `${(y(d.avg) / height) * host.clientHeight}px`);
      tip.selectAll("*").remove();
      tip.append("strong").text(fmt(d.t));
      tip.append("div").text(`avg ${d.avg.toFixed(2)}${suffix}`);
      tip.append("div").text(`min ${d.min}${suffix} · max ${d.max}${suffix}`);
      tip.append("div").text(`${d.count} reading${d.count === 1 ? "" : "s"}`);
    })
    .on("pointerleave", () => {
      focus.attr("visibility", "hidden");
      tip.attr("hidden", true);
    });
}

export function renderDonut(host, d3, items, { centerLabel = "" } = {}) {
  host.replaceChildren();
  const total = d3.sum(items, (d) => d.value);
  if (!total) {
    host.append(note("No sensors to show."));
    return;
  }
  const size = 200;
  const svg = d3.select(host).append("svg").attr("class", "donut").attr("viewBox", `0 0 ${size} ${size}`)
    .attr("role", "img").attr("aria-label", `Donut chart: ${items.map((d) => `${d.label} ${d.value}`).join(", ")}`);
  const g = svg.append("g").attr("transform", `translate(${size / 2},${size / 2})`);
  const arc = d3.arc().innerRadius(62).outerRadius(96).padAngle(0.02);
  g.selectAll("path").data(d3.pie().sort(null).value((d) => d.value)(items)).join("path")
    .attr("class", (_, i) => `slice slice-${i % 6}`).attr("d", arc)
    .append("title").text((d) => `${d.data.label}: ${d.data.value}`);
  g.append("text").attr("class", "donut-total").attr("text-anchor", "middle").attr("dy", "0.1em").text(total);
  if (centerLabel) g.append("text").attr("class", "donut-label").attr("text-anchor", "middle").attr("dy", "1.6em").text(centerLabel);

  const legend = document.createElement("ul");
  legend.className = "legend";
  items.forEach((d, i) => {
    const li = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = `swatch slice-${i % 6}`;
    li.append(swatch, ` ${d.label} (${d.value})`);
    legend.append(li);
  });
  host.append(legend);
}
