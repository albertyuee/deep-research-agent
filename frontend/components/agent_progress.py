"""Agent progress visualization component for Streamlit."""

from __future__ import annotations

import time

import streamlit as st


class AgentProgressDisplay:
    """Manages the real-time agent progress display in Streamlit."""

    @staticmethod
    def _init_session_state():
        defaults = {
            "agent_steps": [],
            "current_step": "",
            "current_detail": "",
            "research_plan": [],
            "retrieval_progress": {},
            "critique_results": [],
            "retry_count": 0,
            "started_at": None,
            # Event log
            "event_log": [],
            # Phase timing
            "phase_start_times": {},
            "phase_durations": {},
            # Retry history
            "retry_history": [],
            # Phase states for stepper: waiting | running | complete | error
            "phase_states": {
                "decomposition": "waiting",
                "retrieval": "waiting",
                "critique": "waiting",
                "synthesis": "waiting",
            },
            # Progress value from backend (0.0 - 1.0)
            "progress_value": 0.0,
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    def handle_event(self, event_type: str, data: dict) -> None:
        if event_type == "heartbeat":
            return
        if event_type.startswith("_"):
            return

        self._init_session_state()

        handler = {
            "research_plan_start": self._on_plan_start,
            "research_plan_chunk": self._on_plan_chunk,
            "retrieval_start": self._on_retrieval_start,
            "retrieval_result": self._on_retrieval_result,
            "critique_start": self._on_critique_start,
            "critique_result": self._on_critique_result,
            "retry_triggered": self._on_retry_triggered,
            "synthesis_start": self._on_synthesis_start,
            "synthesis_chunk": self._on_synthesis_chunk,
            "done": self._on_done,
            "error": self._on_error,
            "cancelled": self._on_cancelled,
        }.get(event_type)

        if handler:
            handler(data)

        st.session_state["agent_steps"].append((event_type, data))

        # Update progress value from SSE event data
        progress = data.get("progress")
        if progress is not None and isinstance(progress, (int, float)):
            st.session_state["progress_value"] = float(progress)
        else:
            # Fallback: estimate progress based on phase
            st.session_state["progress_value"] = _estimate_progress(event_type, data)

        # Append to event log with timestamp
        elapsed = 0.0
        started_at = st.session_state.get("started_at")
        if started_at:
            elapsed = time.time() - started_at

        summary = _summarize_event(event_type, data)
        st.session_state["event_log"].append({
            "elapsed": elapsed,
            "event_type": event_type,
            "summary": summary,
            "data": data,
        })
        # Keep only recent events to bound memory
        max_log = 500
        if len(st.session_state["event_log"]) > max_log:
            st.session_state["event_log"] = st.session_state["event_log"][-max_log:]

    # ── Event handlers ──

    def _on_plan_start(self, data: dict) -> None:
        st.session_state["current_step"] = "planning"
        st.session_state["current_detail"] = "正在拆解研究问题..."
        st.session_state["research_plan"] = []
        st.session_state["started_at"] = time.time()
        st.session_state["event_log"] = []
        st.session_state["phase_durations"] = {}
        st.session_state["phase_start_times"] = {"decomposition": time.time()}
        st.session_state["retry_history"] = []
        st.session_state["phase_states"] = {
            "decomposition": "running",
            "retrieval": "waiting",
            "critique": "waiting",
            "synthesis": "waiting",
        }
        st.session_state["progress_value"] = 0.05

    def _on_plan_chunk(self, data: dict) -> None:
        st.session_state["research_plan"].append({
            "index": data.get("index", 0),
            "question": data.get("question", ""),
            "strategy": data.get("strategy", ""),
            "rationale": data.get("rationale", ""),
        })
        # Record decomposition duration on first chunk
        if "decomposition" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("decomposition")
            st.session_state.get("phase_durations", {})["disassembly"] = time.time() - start
            # Mark decomposition as complete
            phases = st.session_state.get("phase_states", {})
            phases["decomposition"] = "complete"

    def _on_retrieval_start(self, data: dict) -> None:
        step = data.get("step", 0)
        total = data.get("total", 0)
        strategy_name = {"semantic": "语义", "keyword": "关键词", "hybrid": "混合"}.get(
            data.get("strategy", ""), data.get("strategy", "")
        )
        retry = data.get("retry_count", 0)
        st.session_state["current_step"] = "retrieving"
        st.session_state["current_detail"] = f"正在检索 子问题 {step}/{total}（{strategy_name}策略）"
        st.session_state["retrieval_progress"] = {
            "step": step,
            "total": total,
            "strategy": data.get("strategy", ""),
            "retry": retry,
        }
        st.session_state["retry_count"] = retry
        phase_key = f"retrieval_step_{step}"
        st.session_state.get("phase_start_times", {})[phase_key] = time.time()
        phases = st.session_state.get("phase_states", {})
        phases["retrieval"] = "running"

    def _on_retrieval_result(self, data: dict) -> None:
        count = data.get("result_count", 0)
        top = data.get("top_score", 0)
        preview = data.get("top_preview", "")
        st.session_state["retrieval_progress"]["results"] = count
        st.session_state["retrieval_progress"]["top_score"] = top
        st.session_state["retrieval_progress"]["top_preview"] = preview
        st.session_state["current_detail"] = f"检索完成，找到 {count} 条结果（最高相似度: {top:.2f})"
        phase_key = f"retrieval_step_{data.get('step', 0)}"
        if phase_key in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop(phase_key)
            st.session_state.get("phase_durations", {})[f"retrieval_step_{data.get('step', 0)}"] = time.time() - start

    def _on_critique_start(self, data: dict) -> None:
        st.session_state["current_step"] = "evaluating"
        st.session_state["current_detail"] = "正在评估检索质量..."
        st.session_state.get("phase_start_times", {})["critique"] = time.time()
        phases = st.session_state.get("phase_states", {})
        phases["retrieval"] = "complete"
        phases["critique"] = "running"

    def _on_critique_result(self, data: dict) -> None:
        passed = data.get("passed", False)
        score = data.get("composite_score", 0)
        reasoning = data.get("reasoning", "")
        retry_suggestion = data.get("retry_suggestion", "")
        st.session_state["critique_results"].append({
            "step": data.get("step", 0),
            "score": score,
            "relevance": data.get("relevance", 0),
            "completeness": data.get("completeness", 0),
            "passed": passed,
            "reasoning": reasoning,
            "retry_suggestion": retry_suggestion,
        })
        status_text = "通过" if passed else "不通过"
        st.session_state["current_detail"] = f"质量评估: {score:.2f} 分 — {status_text}"
        if "critique" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("critique")
            st.session_state.get("phase_durations", {})["evaluation"] = time.time() - start
        phases = st.session_state.get("phase_states", {})
        phases["critique"] = "complete"
        if passed:
            phases["synthesis"] = "running"
        else:
            phases["synthesis"] = "waiting"

    def _on_retry_triggered(self, data: dict) -> None:
        count = data.get("count", 0)
        st.session_state["current_step"] = "retrying"
        st.session_state["current_detail"] = f"检索质量不达标，正在第 {count} 次重试（改写查询）..."
        last_critique = (
            st.session_state.get("critique_results", [])[-1]
            if st.session_state.get("critique_results")
            else {}
        )
        st.session_state["retry_history"].append({
            "attempt": count,
            "score": last_critique.get("score", 0),
            "suggestion": last_critique.get("retry_suggestion", ""),
        })
        # On retry, go back to retrieval phase
        phases = st.session_state.get("phase_states", {})
        phases["critique"] = "complete"
        phases["retrieval"] = "running"
        phases["synthesis"] = "waiting"

    def _on_synthesis_start(self, data: dict) -> None:
        st.session_state["current_step"] = "synthesizing"
        st.session_state["current_detail"] = "正在聚合多源信息，生成研究报告..."
        st.session_state.get("phase_start_times", {})["synthesis"] = time.time()
        phases = st.session_state.get("phase_states", {})
        phases["critique"] = "complete"
        phases["synthesis"] = "running"

    def _on_synthesis_chunk(self, data: dict) -> None:
        pass

    def _on_done(self, data: dict) -> None:
        st.session_state["current_step"] = "done"
        st.session_state["current_detail"] = f"研究完成，报告共 {data.get('report_length', 0)} 字符"
        st.session_state["progress_value"] = 1.0
        if "synthesis" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("synthesis")
            st.session_state.get("phase_durations", {})["synthesis"] = time.time() - start
        phases = st.session_state.get("phase_states", {})
        phases["synthesis"] = "complete"

    def _on_error(self, data: dict) -> None:
        # Save previous step before overwriting so we can mark the right phase
        previous_step = st.session_state.get("current_step", "")
        st.session_state["current_step"] = "error"
        st.session_state["current_detail"] = data.get("message", "发生错误")
        phase_map = {"planning": "decomposition", "retrieving": "retrieval",
                      "evaluating": "critique", "synthesizing": "synthesis"}
        phase_key = phase_map.get(previous_step)
        if phase_key:
            st.session_state.get("phase_states", {})[phase_key] = "error"

    def _on_cancelled(self, data: dict) -> None:
        # Save previous step before overwriting so we can mark the right phase
        previous_step = st.session_state.get("current_step", "")
        st.session_state["current_step"] = "cancelled"
        st.session_state["current_detail"] = data.get("message", "研究已取消")
        st.session_state["progress_value"] = st.session_state.get("progress_value", 0.0)
        phase_map = {"planning": "decomposition", "retrieving": "retrieval",
                      "evaluating": "critique", "synthesizing": "synthesis"}
        phase_key = phase_map.get(previous_step)
        if phase_key:
            st.session_state.get("phase_states", {})[phase_key] = "error"


# ──────────────────── Progress estimation ────────────────────


def _estimate_progress(event_type: str, data: dict) -> float:
    """Estimate progress based on event type when no 'progress' field in data."""
    estimates = {
        "research_plan_start": 0.05,
        "research_plan_chunk": 0.10,
        "retrieval_start": 0.15,
        "retrieval_result": 0.35,
        "critique_start": 0.40,
        "critique_result": 0.50,
        "retry_triggered": 0.35,
        "synthesis_start": 0.60,
        "synthesis_chunk": 0.75,
        "done": 1.0,
        "error": 0.0,
    }
    return estimates.get(event_type, st.session_state.get("progress_value", 0.0))


# ──────────────────── Event summary helper ────────────────────


def _summarize_event(event_type: str, data: dict) -> str:
    if event_type == "research_plan_start":
        q = data.get("query", "")
        return f"开始拆解: {q[:60]}"
    elif event_type == "research_plan_chunk":
        idx = data.get("index", "?")
        q = data.get("question", "")
        s = data.get("strategy", "")
        return f"子问题 #{idx}: {q[:50]} (策略: {s})"
    elif event_type == "retrieval_start":
        s = data.get("step", "?")
        t = data.get("total", "?")
        strategy = data.get("strategy", "")
        return f"检索 {s}/{t} (策略: {strategy})"
    elif event_type == "retrieval_result":
        count = data.get("result_count", 0)
        top = data.get("top_score", 0)
        return f"检索完成: {count} 条结果, top={top:.3f}"
    elif event_type == "critique_start":
        return f"评估检索质量 (步骤 {data.get('step', '?')})"
    elif event_type == "critique_result":
        s = data.get("composite_score", 0)
        p = "PASS" if data.get("passed") else "FAIL"
        return f"评估结果: {s:.3f} [{p}]"
    elif event_type == "retry_triggered":
        return f"触发重试 #{data.get('count', '?')}"
    elif event_type == "synthesis_start":
        return f"开始生成报告 ({data.get('total_steps', '?')} 步骤聚合)"
    elif event_type == "synthesis_chunk":
        return f"报告片段: {data.get('text', '')[:60]}..."
    elif event_type == "done":
        return f"完成, 报告长度: {data.get('report_length', 0)} 字符"
    elif event_type == "error":
        return f"错误: {data.get('message', '')[:80]}"
    return ""


# ──────────────────── Color coding ────────────────────


def _color_class(score: float) -> str:
    """Return CSS class name based on score threshold."""
    if score >= 0.7:
        return "score-pass"
    elif score >= 0.4:
        return "score-warn"
    else:
        return "score-fail"


def _score_html(score: float, label: str = "") -> str:
    """Render a score with color-coded HTML span."""
    cls = _color_class(score)
    if label:
        return f'<span class="{cls}">{label}: {score:.2f}</span>'
    return f'<span class="{cls}">{score:.2f}</span>'


def _score_bar(score: float) -> str:
    """Render a mini score bar as HTML."""
    pct = min(max(int(score * 100), 0), 100)
    bar_cls = "pass" if score >= 0.7 else ("warn" if score >= 0.4 else "fail")
    return (
        f'<div class="score-bar-bg">'
        f'<div class="score-bar-fill {bar_cls}" style="width:{pct}%;"></div>'
        f'</div>'
    )


# ──────────────────── Render functions ────────────────────


def _render_stepper():
    """Render a custom HTML/CSS step indicator with status dots."""
    phases = st.session_state.get("phase_states", {
        "decomposition": "waiting",
        "retrieval": "waiting",
        "critique": "waiting",
        "synthesis": "waiting",
    })

    phase_labels = {
        "decomposition": "拆解问题",
        "retrieval": "检索",
        "critique": "评估",
        "synthesis": "合成报告",
    }
    phase_icons = {
        "decomposition": "1",
        "retrieval": "2",
        "critique": "3",
        "synthesis": "4",
    }

    keys = ["decomposition", "retrieval", "critique", "synthesis"]
    html_parts = ['<div class="stepper">']

    for i, key in enumerate(keys):
        state = phases.get(key, "waiting")
        icon = phase_icons[key]
        label = phase_labels[key]

        if state == "complete":
            icon = "✓"
        elif state == "error":
            icon = "✗"

        active_class = "active" if state in ("running", "complete") else ""
        html_parts.append(
            f'<div class="stepper-step">'
            f'<div class="stepper-dot {state}">{icon}</div>'
            f'<div class="stepper-label {active_class}">{label}</div>'
            f'</div>'
        )

        # Add connector between steps
        if i < len(keys) - 1:
            next_key = keys[i + 1]
            next_state = phases.get(next_key, "waiting")
            connector_class = "done" if state == "complete" else ""
            html_parts.append(f'<div class="stepper-connector {connector_class}"></div>')

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_event_log():
    """Render the real-time SSE event log panel (collapsed by default)."""
    events = st.session_state.get("event_log", [])
    if not events:
        st.caption("暂无事件")
        return

    with st.expander("📜 事件日志", expanded=False):
        lines = ["| 时间 | 事件 | 摘要 |", "|------|------|------|"]
        for r in events[-50:]:
            lines.append(f"| {r['elapsed']:.1f}s | `{r['event_type']}` | {r['summary']} |")
        st.markdown("\n".join(lines))

        with st.expander("查看完整事件数据", expanded=False):
            for i, evt in enumerate(events[-10:]):
                key = f"payload_{i}_{len(events)}"
                with st.expander(f"[{evt['elapsed']:.1f}s] {evt['event_type']}", expanded=False):
                    try:
                        st.json(evt["data"], key=key)
                    except Exception:
                        st.text(str(evt["data"])[:500])


def _render_timing_stats():
    """Render per-phase timing statistics."""
    durations = st.session_state.get("phase_durations", {})
    if not durations:
        st.caption("暂无数据")
        return

    label_map = {
        "disassembly": "拆解问题",
        "evaluation": "质量评估",
        "synthesis": "合成报告",
    }
    total_time = 0.0
    lines = ["| 阶段 | 耗时 |", "|------|------|"]
    for key, dur in durations.items():
        label = label_map.get(key, key.replace("retrieval_step_", "检索步骤 "))
        lines.append(f"| {label} | {dur:.1f}s |")
        total_time += dur

    st.markdown("\n".join(lines))
    st.caption(f"累计: {total_time:.1f}s")


def _render_retry_history():
    """Render retry history panel (only when retries occurred)."""
    history = st.session_state.get("retry_history", [])
    if not history:
        return

    with st.expander("🔄 重试历史", expanded=False):
        for h in history:
            st.markdown(
                f"**第 {h['attempt']} 次重试** — "
                f"上次评分: {_score_html(h['score'])} | "
                f"建议: *{h.get('suggestion', 'N/A')}*",
                unsafe_allow_html=True,
            )


def render_progress_panel():
    """Render the agent progress visualization panel."""
    current = st.session_state.get("current_step", "")
    detail = st.session_state.get("current_detail", "")
    plan = st.session_state.get("research_plan", [])
    critiques = st.session_state.get("critique_results", [])
    retrieval = st.session_state.get("retrieval_progress", {})
    progress_value = st.session_state.get("progress_value", 0.0)

    # ── Stepper ──
    _render_stepper()

    # ── Current status ──
    if detail:
        if current == "error":
            st.error(f"**当前状态**: {detail}")
        elif current == "retrying":
            st.warning(f"**当前状态**: {detail}")
        elif current == "cancelled":
            st.warning(f"**当前状态**: {detail}")
        elif current == "done":
            st.success(f"**当前状态**: {detail}")
        else:
            st.info(f"**{detail}**")

    # ── Research plan ──
    if plan:
        with st.expander("📋 研究计划", expanded=len(plan) <= 3):
            for p in plan:
                strategy_icon = {"semantic": "🧠", "keyword": "🔑", "hybrid": "🔀"}.get(
                    p.get("strategy", ""), "❓"
                )
                rationale = p.get("rationale", "")
                line = f"{p['index']}. {strategy_icon} **{p['question']}**"
                if rationale:
                    line += f"  \n> 选择理由: *{rationale}*"
                st.markdown(line)

    # ── Retrieval details ──
    if retrieval:
        with st.expander("🔍 检索详情", expanded=False):
            step = retrieval.get("step", 0)
            total = retrieval.get("total", 0)
            strategy = retrieval.get("strategy", "")
            results = retrieval.get("results", 0)
            top_score = retrieval.get("top_score", 0)
            retry = retrieval.get("retry", 0)
            preview = retrieval.get("top_preview", "")

            st.markdown(f"**步骤**: {step}/{total} | **策略**: `{strategy}` | **重试**: {retry} 次")
            if retry > 0:
                st.warning(f"已重试 {retry} 次")
            st.markdown(
                f"**结果数**: {results} | **最高相似度**: {_score_html(top_score)} | {_score_bar(top_score)}",
                unsafe_allow_html=True,
            )
            if preview:
                key = f"preview_{step}_{total}"
                with st.expander("最佳结果预览", expanded=False):
                    st.text(preview)

    # ── Critique details ──
    if critiques:
        with st.expander("✅ 检索质量详情", expanded=False):
            for c in critiques:
                status_icon = "✅" if c["passed"] else "⚠️"
                score = c["score"]
                relevance = c.get("relevance", 0)
                completeness = c.get("completeness", 0)
                st.markdown(
                    f"{status_icon} **步骤 {c['step']}**: "
                    f"综合 {_score_html(score)} "
                    f"(相关性 {_score_html(relevance)} / 完整性 {_score_html(completeness)})",
                    unsafe_allow_html=True,
                )
                st.markdown(_score_bar(score), unsafe_allow_html=True)
                reasoning = c.get("reasoning", "")
                if reasoning:
                    key = f"reasoning_{c['step']}_{len(critiques)}"
                    with st.expander(f"评分推理 (步骤 {c['step']})", expanded=False):
                        st.text(reasoning)
                retry_sug = c.get("retry_suggestion", "")
                if not c["passed"] and retry_sug:
                    st.caption(f"💡 重试建议: *{retry_sug}*")

    # ── Progress bar ──
    if current == "done":
        st.progress(1.0, text="研究完成")
    elif current == "cancelled":
        st.progress(progress_value, text="研究已取消")
    elif current not in ("error", ""):
        st.progress(min(max(progress_value, 0.05), 0.98), text="Agent 思考中...")

    # ── Elapsed time ──
    started_at = st.session_state.get("started_at")
    if started_at and current not in ("done", "error", "cancelled", ""):
        elapsed = time.time() - started_at
        st.caption(f"⏱ 已用时: {elapsed:.0f} 秒")
