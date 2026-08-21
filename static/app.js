// --- JurisSearch Frontend Logic ---

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const suggestionsDropdown = document.getElementById("suggestions");

    const toggleConfigBtn = document.getElementById("toggle-config-btn");
    const configPanel = document.getElementById("config-panel");
    const toggleIcon = document.getElementById("toggle-icon");

    // Sliders & Values
    const sliders = ["alpha", "beta", "gamma", "delta"];
    const weights = {};
    sliders.forEach(s => {
        const input = document.getElementById(`weight-${s}`);
        const span = document.getElementById(`val-${s}`);
        weights[s] = parseFloat(input.value);
        input.addEventListener("input", (e) => {
            weights[s] = parseFloat(e.target.value);
            span.textContent = weights[s].toFixed(2);
        });
    });

    const excludeOverruledCheck = document.getElementById("exclude-overruled-check");
    const courtSelect = document.getElementById("court-select");

    const resultsList = document.getElementById("results-list");
    const resultsCount = document.getElementById("results-count");
    const queryTime = document.getElementById("query-time");

    // Case Details UI
    const detailsColumn = document.getElementById("details-column");
    const detailsPlaceholder = document.getElementById("details-placeholder");
    const detailsContent = document.getElementById("details-content");
    const detailsCourtBadge = document.getElementById("details-court-badge");
    const detailsOverruledBadge = document.getElementById("details-overruled-badge");
    const detailsCautionBadge = document.getElementById("details-caution-badge");
    const detailsName = document.getElementById("details-name");
    const detailsCitation = document.getElementById("details-citation");
    const detailsJurisdiction = document.getElementById("details-jurisdiction");
    const detailsDate = document.getElementById("details-date");
    const detailsJudges = document.getElementById("details-judges");
    const detailsPageRank = document.getElementById("details-pagerank");
    const detailsOpinion = document.getElementById("details-opinion");

    // Tab Panes
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    // State
    let currentActiveDocId = null;
    let suggestDebounceTimeout = null;

    // Store full result objects keyed by doc_id so breakdown tab can access them
    const resultDataMap = {};

    // ─── 1. Load Corpus Stats ───────────────────────────────────────────────────
    async function loadStats() {
        try {
            const res = await fetch("/api/stats");
            if (!res.ok) throw new Error("Stats failed");
            const data = await res.json();
            document.getElementById("stat-cases").textContent = data.total_documents;
            document.getElementById("stat-vocab").textContent = data.vocabulary_size.toLocaleString();
            document.getElementById("stat-overruled").textContent = data.overruled_count;
            document.getElementById("stat-pagerank").textContent = data.pagerank_max.toFixed(4);
        } catch (err) {
            console.error("Failed to load engine statistics:", err);
        }
    }
    loadStats();

    // ─── 2. Advanced Tuning Panel Toggle ────────────────────────────────────────
    toggleConfigBtn.addEventListener("click", () => {
        configPanel.classList.toggle("hidden");
        toggleConfigBtn.classList.toggle("open");
        toggleIcon.style.transform = configPanel.classList.contains("hidden")
            ? "rotate(0deg)"
            : "rotate(180deg)";
    });

    // ─── 3. Autocomplete / Auto-Suggest ─────────────────────────────────────────
    searchInput.addEventListener("input", () => {
        clearTimeout(suggestDebounceTimeout);
        const val = searchInput.value.trim();
        if (val.length < 2) {
            suggestionsDropdown.style.display = "none";
            return;
        }
        suggestDebounceTimeout = setTimeout(async () => {
            try {
                const res = await fetch(`/api/suggest?q=${encodeURIComponent(val)}`);
                if (!res.ok) throw new Error("Suggestion failed");
                const categories = await res.json();
                renderSuggestions(categories);
            } catch (err) {
                console.error("Autocomplete error:", err);
            }
        }, 150);
    });

    document.addEventListener("click", (e) => {
        if (!e.target.closest(".search-bar-wrapper")) {
            suggestionsDropdown.style.display = "none";
        }
    });

    function renderSuggestions(categories) {
        suggestionsDropdown.innerHTML = "";
        let hasSuggestions = false;

        const catNames = {
            "case_names": "Case Names",
            "citations": "Citations",
            "judges": "Judges",
            "legal_terms": "Legal Concepts"
        };

        for (const [key, items] of Object.entries(categories)) {
            if (!items || items.length === 0) continue;
            hasSuggestions = true;

            const catDiv = document.createElement("div");
            catDiv.className = "suggestions-category";

            const title = document.createElement("div");
            title.className = "suggestions-category-title";
            title.textContent = catNames[key] || key;
            catDiv.appendChild(title);

            items.forEach(item => {
                const suggestItem = document.createElement("div");
                suggestItem.className = "suggest-item";

                const termSpan = document.createElement("span");
                termSpan.className = "suggest-item-term";
                termSpan.textContent = item.term;

                const metaSpan = document.createElement("span");
                metaSpan.className = "suggest-item-meta";
                metaSpan.textContent = (key === "case_names" || key === "citations") ? "Jump to case" : "";

                suggestItem.appendChild(termSpan);
                suggestItem.appendChild(metaSpan);

                suggestItem.addEventListener("click", () => {
                    searchInput.value = item.term;
                    suggestionsDropdown.style.display = "none";
                    if (item.doc_ids && item.doc_ids.length > 0) {
                        viewCaseDetails(item.doc_ids[0]);
                    } else {
                        executeSearch();
                    }
                });

                catDiv.appendChild(suggestItem);
            });

            suggestionsDropdown.appendChild(catDiv);
        }

        suggestionsDropdown.style.display = hasSuggestions ? "block" : "none";
    }

    // ─── 4. Execute Search ───────────────────────────────────────────────────────
    searchBtn.addEventListener("click", executeSearch);
    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            suggestionsDropdown.style.display = "none";
            executeSearch();
        }
    });

    async function executeSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        const courtFilter = courtSelect.value;
        const exclOverruled = excludeOverruledCheck.checked;

        let url = `/api/search?q=${encodeURIComponent(query)}`;
        if (courtFilter) url += `&court=${courtFilter}`;
        url += `&exclude_overruled=${exclOverruled}`;
        url += `&alpha=${weights.alpha}&beta=${weights.beta}&gamma=${weights.gamma}&delta=${weights.delta}`;

        try {
            resultsList.innerHTML = `<div class="empty-state"><p>Searching index…</p></div>`;
            resultsCount.textContent = "Searching…";
            queryTime.textContent = "";

            const res = await fetch(url);
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Search API call failed");
            }
            const data = await res.json();
            renderSearchResults(data);
        } catch (err) {
            console.error(err);
            resultsList.innerHTML = `<div class="empty-state text-red"><p>Search failed: ${err.message}</p></div>`;
        }
    }

    function courtLabel(level) {
        if (level === 1) return "Supreme Court";
        if (level === 2) return "Appellate Court";
        return "District Court";
    }

    function renderSearchResults(data) {
        resultsList.innerHTML = "";
        // Clear stale result data
        Object.keys(resultDataMap).forEach(k => delete resultDataMap[k]);

        if (data.total_results === 0) {
            resultsCount.textContent = "No results found.";
            queryTime.textContent = `(${data.query_time_ms} ms)`;
            resultsList.innerHTML = `
                <div class="empty-state">
                    <h3>No Cases Found</h3>
                    <p>Try broader search terms or adjust the filters.</p>
                </div>`;
            return;
        }

        resultsCount.textContent = `Found ${data.total_results} matching case${data.total_results !== 1 ? "s" : ""}`;
        queryTime.textContent = `(${data.query_time_ms} ms)`;

        data.results.forEach(result => {
            // Store full result data for breakdown tab
            resultDataMap[result.doc_id] = result;

            const card = document.createElement("div");
            card.className = `result-card ${currentActiveDocId === result.doc_id ? "active" : ""}`;
            card.setAttribute("data-id", result.doc_id);

            // ── Badges ──
            let statusBadge = "";
            if (result.is_overruled) {
                statusBadge = `<span class="badge text-red">⚠ Overruled</span>`;
            } else if (result.is_caution) {
                statusBadge = `<span class="badge text-caution">⚡ Caution</span>`;
            }

            const bm25Raw = result.score_breakdown.bm25_raw ?? 0;
            const prRaw  = result.score_breakdown.pagerank_raw ?? 0;

            card.innerHTML = `
                <div class="result-top">
                    <div class="result-title-area">
                        <h3>${escapeHtml(result.case_name)}</h3>
                        <span class="result-citation">${escapeHtml(result.citation)}</span>
                    </div>
                    <div class="badges-row">
                        <span class="badge badge-court-${result.court_level}">${courtLabel(result.court_level)}</span>
                        ${statusBadge}
                    </div>
                </div>
                <p class="result-snippet">${result.snippet}</p>
                <div class="result-bottom">
                    <div class="result-scores">
                        <span class="score-tag">BM25: <strong>${bm25Raw.toFixed(2)}</strong></span>
                        <span class="score-tag">PR: <strong>${prRaw.toFixed(4)}</strong></span>
                        <span class="score-tag">Decided: <strong>${result.date_decided}</strong></span>
                    </div>
                    <div class="result-rank-score">Score: ${result.score.toFixed(3)}</div>
                </div>`;

            card.addEventListener("click", () => {
                document.querySelectorAll(".result-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                viewCaseDetails(result.doc_id);
            });

            resultsList.appendChild(card);
        });
    }

    // ─── 5. Fetch and Render Case Details ────────────────────────────────────────
    async function viewCaseDetails(doc_id) {
        currentActiveDocId = doc_id;

        document.querySelectorAll(".result-card").forEach(c => {
            c.classList.toggle("active", c.getAttribute("data-id") === doc_id);
        });

        try {
            detailsPlaceholder.classList.add("hidden");
            detailsContent.classList.add("hidden");
            detailsColumn.classList.remove("empty");

            const res = await fetch(`/api/case/${encodeURIComponent(doc_id)}`);
            if (!res.ok) throw new Error("Failed to load case detail");
            const data = await res.json();

            renderCaseDetails(data);
        } catch (err) {
            console.error(err);
            detailsPlaceholder.classList.remove("hidden");
            detailsContent.classList.add("hidden");
            detailsColumn.classList.add("empty");
        }
    }

    function renderCaseDetails(data) {
        detailsContent.classList.remove("hidden");

        const meta = data.metadata;
        detailsName.textContent = meta.case_name;
        detailsCitation.textContent = meta.citation;
        detailsJurisdiction.textContent = meta.jurisdiction;
        detailsDate.textContent = meta.date_decided;
        detailsJudges.textContent = Array.isArray(meta.judges) ? meta.judges.join(", ") : meta.judges;
        detailsPageRank.textContent = data.pagerank.toFixed(5);

        detailsCourtBadge.textContent = courtLabel(meta.court_level);
        detailsCourtBadge.className = `badge badge-court-${meta.court_level}`;

        // ── Overruled / Caution badges ──
        if (data.is_overruled) {
            detailsOverruledBadge.classList.remove("hidden");
            const by = data.overruled_by && data.overruled_by.length > 0
                ? ` by: ${data.overruled_by.join(", ")}`
                : "";
            detailsOverruledBadge.textContent = `⚠ OVERRULED${by}`;
            detailsCautionBadge.classList.add("hidden");
        } else {
            detailsOverruledBadge.classList.add("hidden");
            if (data.is_caution) {
                detailsCautionBadge.classList.remove("hidden");
                const relied = data.cautions_relied_on && data.cautions_relied_on.length > 0
                    ? ` — relies on overruled: ${data.cautions_relied_on.join(", ")}`
                    : "";
                detailsCautionBadge.textContent = `⚡ CAUTION${relied}`;
            } else {
                detailsCautionBadge.classList.add("hidden");
            }
        }

        // ── Opinion Text (reset scroll) ──
        detailsOpinion.textContent = meta.opinion_text;
        detailsOpinion.scrollTop = 0;

        // ── Citation Graph ──
        renderCitationGraph(data);

        // ── Score Breakdown (uses stored search result data if available) ──
        renderScoreBreakdown(meta.doc_id);

        // Reset tabs to Opinion tab
        tabButtons.forEach(b => b.classList.remove("active"));
        tabPanes.forEach(p => p.classList.remove("active"));
        tabButtons[0].classList.add("active");
        tabPanes[0].classList.add("active");
    }

    // ─── 6. SVG Citation Graph ────────────────────────────────────────────────────
    function renderCitationGraph(data) {
        const svg = document.getElementById("citation-svg");
        svg.innerHTML = "";

        const currentId  = data.metadata.doc_id;
        const currentCit = data.metadata.citation;
        const parents    = data.citations_in  || [];
        const children   = data.citations_out || [];

        const W = 600, H = 450;
        const cx = W / 2, cy = H / 2;

        const NS = "http://www.w3.org/2000/svg";
        function el(tag, attrs) {
            const e = document.createElementNS(NS, tag);
            for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
            return e;
        }

        const treatmentColors = {
            "followed":       "#10B981",
            "cited_generally": "#06B6D4",
            "distinguished":  "#F97316",
            "overruled":      "#EF4444"
        };

        // ── Arrow markers ──
        const defs = el("defs", {});
        Object.entries(treatmentColors).forEach(([t, color]) => {
            const marker = el("marker", {
                id: `arrow-${t}`,
                viewBox: "0 0 10 10",
                refX: "22", refY: "5",
                markerWidth: "6", markerHeight: "6",
                orient: "auto-start-reverse"
            });
            marker.appendChild(el("path", { d: "M 0 1 L 10 5 L 0 9 z", fill: color }));
            defs.appendChild(marker);
        });
        svg.appendChild(defs);

        // ── Node layout ──
        const distributeY = (n, idx) => n > 1 ? 50 + idx * (350 / (n - 1)) : cy;

        const leftNodes  = parents.map((p, i) => ({ x: 100, y: distributeY(parents.length, i), data: p }));
        const rightNodes = children.map((c, i) => ({ x: 500, y: distributeY(children.length, i), data: c }));

        // ── Draw edges ──
        const drawEdge = (x1, y1, x2, y2, treatment) => {
            const color = treatmentColors[treatment] || "#9CA3AF";
            const midX = (x1 + x2) / 2;
            svg.appendChild(el("path", {
                d: `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`,
                stroke: color,
                "stroke-width": "2",
                fill: "none",
                "marker-end": `url(#arrow-${treatment in treatmentColors ? treatment : "cited_generally"})`
            }));
        };

        leftNodes.forEach(n => drawEdge(n.x, n.y, cx, cy, n.data.treatment));
        rightNodes.forEach(n => drawEdge(cx, cy, n.x, n.y, n.data.treatment));

        // ── Draw nodes ──
        const drawNode = (x, y, citLabel, title, docId, level, isCenter) => {
            const strokeColor = level === 1 ? "#F59E0B" : level === 2 ? "#06B6D4" : "#6366F1";
            const radius = isCenter ? 25 : 18;
            const g = el("g", { style: "cursor: pointer" });

            const circle = el("circle", {
                cx: x, cy: y, r: radius,
                fill: isCenter ? "rgba(13,17,30,0.95)" : "rgba(31,41,55,0.95)",
                stroke: strokeColor,
                "stroke-width": isCenter ? "3" : "1.5",
                filter: isCenter ? "drop-shadow(0px 0px 8px rgba(99,102,241,0.6))" : "none"
            });

            const titleEl = document.createElementNS(NS, "title");
            titleEl.textContent = `${title} (${citLabel})`;
            circle.appendChild(titleEl);
            g.appendChild(circle);

            const label = el("text", {
                x, y: y + 4,
                "text-anchor": "middle",
                fill: "#F3F4F6",
                "font-size": isCenter ? "10px" : "8px"
            });
            label.textContent = citLabel.replace(/\s+/g, "");
            g.appendChild(label);

            g.addEventListener("click", () => viewCaseDetails(docId));
            svg.appendChild(g);
        };

        leftNodes.forEach(n => drawNode(n.x, n.y, n.data.citation, n.data.case_name, n.data.doc_id, n.data.court_level, false));
        rightNodes.forEach(n => drawNode(n.x, n.y, n.data.citation, n.data.case_name, n.data.doc_id, n.data.court_level, false));
        drawNode(cx, cy, currentCit, data.metadata.case_name, currentId, data.metadata.court_level, true);
    }

    // ─── 7. Score Breakdown Pane ─────────────────────────────────────────────────
    // Uses real score_breakdown data stored in resultDataMap
    function renderScoreBreakdown(docId) {
        const chart = document.getElementById("breakdown-chart");
        chart.innerHTML = "";

        const result = resultDataMap[docId];
        if (!result) {
            chart.innerHTML = `
                <div class="empty-state">
                    <p>Score breakdown is available for cases found via search.<br>
                    Use the search bar and click a result to see its breakdown.</p>
                </div>`;
            return;
        }

        const sb = result.score_breakdown;

        const components = [
            {
                name: "Text Relevance (BM25)",
                cssClass: "fill-bm25",
                weight: weights.alpha,
                rawLabel: `${sb.bm25_raw.toFixed(3)} → norm ${sb.bm25_norm.toFixed(3)}`,
                normValue: sb.bm25_norm
            },
            {
                name: "Authority (PageRank)",
                cssClass: "fill-pr",
                weight: weights.beta,
                rawLabel: `${sb.pagerank_raw.toFixed(5)} → norm ${sb.pagerank_norm.toFixed(3)}`,
                normValue: sb.pagerank_norm
            },
            {
                name: "Court Tier Bias",
                cssClass: "fill-court",
                weight: weights.gamma,
                rawLabel: `${sb.court_weight.toFixed(2)} (tier weight)`,
                normValue: sb.court_weight
            },
            {
                name: "Recency Boost",
                cssClass: "fill-recency",
                weight: weights.delta,
                rawLabel: `${sb.recency_boost.toFixed(4)} (hyperbolic decay)`,
                normValue: sb.recency_boost
            }
        ];

        components.forEach(comp => {
            const row = document.createElement("div");
            row.className = "breakdown-row";
            const barWidth = Math.min(100, comp.normValue * 100);
            row.innerHTML = `
                <div class="breakdown-row-labels">
                    <span>${comp.name} <em style="opacity:.6">(w: ${comp.weight.toFixed(2)})</em></span>
                    <span style="font-size:0.75rem;opacity:.7">${comp.rawLabel}</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill ${comp.cssClass}" style="width: ${barWidth.toFixed(1)}%"></div>
                </div>`;
            chart.appendChild(row);
        });

        // Weighted contribution breakdown
        const contribDiv = document.createElement("div");
        contribDiv.className = "breakdown-contributions";
        contribDiv.innerHTML = `
            <div class="contrib-row">
                <span>α · BM25_norm</span>
                <span>${weights.alpha.toFixed(2)} × ${sb.bm25_norm.toFixed(3)} = <strong>${(weights.alpha * sb.bm25_norm).toFixed(4)}</strong></span>
            </div>
            <div class="contrib-row">
                <span>β · PR_norm</span>
                <span>${weights.beta.toFixed(2)} × ${sb.pagerank_norm.toFixed(3)} = <strong>${(weights.beta * sb.pagerank_norm).toFixed(4)}</strong></span>
            </div>
            <div class="contrib-row">
                <span>γ · Court_weight</span>
                <span>${weights.gamma.toFixed(2)} × ${sb.court_weight.toFixed(2)} = <strong>${(weights.gamma * sb.court_weight).toFixed(4)}</strong></span>
            </div>
            <div class="contrib-row">
                <span>δ · Recency_boost</span>
                <span>${weights.delta.toFixed(2)} × ${sb.recency_boost.toFixed(4)} = <strong>${(weights.delta * sb.recency_boost).toFixed(4)}</strong></span>
            </div>
            <div class="contrib-row total-row">
                <span>Final Score</span>
                <span><strong>${result.score.toFixed(4)}</strong>${result.is_overruled ? " × 0.01 (overruled penalty)" : ""}</span>
            </div>`;
        chart.appendChild(contribDiv);
    }

    // ─── 8. Tab Controller ────────────────────────────────────────────────────────
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.getAttribute("data-tab")).classList.add("active");
        });
    });

    // ─── Utility ─────────────────────────────────────────────────────────────────
    function escapeHtml(str) {
        const d = document.createElement("div");
        d.textContent = str;
        return d.innerHTML;
    }
});
