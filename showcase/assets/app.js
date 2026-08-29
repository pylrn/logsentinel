(() => {
  const tabs = document.querySelector(".environment-tabs");
  const list = document.querySelector("#event-list");
  const detail = document.querySelector("#incident-content");
  let environment = "hdfs";
  let eventIndex = 1;

  const text = (tag, value, className = "") => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    return node;
  };

  function renderDetail(event) {
    detail.replaceChildren();
    const grid = document.createElement("div");
    grid.className = "incident-grid";
    const scores = document.createElement("div");
    scores.append(text("p", "Component contribution", "panel-label"));
    Object.entries(event.components).forEach(([name, value]) => {
      const row = document.createElement("div");
      row.className = "signal";
      const bar = document.createElement("div");
      bar.className = "bar";
      const fill = document.createElement("i");
      fill.style.width = String(Math.round(value * 100)) + "%";
      bar.append(fill);
      row.append(text("span", name), bar, text("strong", value.toFixed(2)));
      scores.append(row);
    });
    const expected = document.createElement("div");
    expected.append(text("p", "Expected next templates", "panel-label"));
    const ordered = document.createElement("ol");
    ordered.className = "expected";
    event.expected.forEach(item => ordered.append(text("li", item)));
    expected.append(ordered);
    detail.append(
      text("span", "● Illustrative replay · score " + event.score.toFixed(2), "provenance"),
      text("h3", event.title),
      text("div", event.template, "template"),
      text("p", event.explanation),
      grid,
    );
    grid.append(scores, expected);
  }

  function renderEvents() {
    list.replaceChildren();
    REPLAY_ENVIRONMENTS[environment].events.forEach((event, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "event-button";
      button.setAttribute("aria-pressed", String(index === eventIndex));
      const title = text("span", event.title, "event-title");
      title.append(text("span", event.score.toFixed(2), "event-score"));
      button.append(text("span", event.time, "event-time"), title);
      button.addEventListener("click", () => { eventIndex = index; render(); });
      list.append(button);
    });
  }

  function renderTabs() {
    tabs.replaceChildren();
    Object.entries(REPLAY_ENVIRONMENTS).forEach(([key, value]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(key === environment));
      button.textContent = value.label;
      button.addEventListener("click", () => { environment = key; eventIndex = 0; render(); });
      tabs.append(button);
    });
  }

  function render() {
    renderTabs();
    renderEvents();
    renderDetail(REPLAY_ENVIRONMENTS[environment].events[eventIndex]);
  }

  render();
})();
