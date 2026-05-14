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
            # ── New: event log ──
            "event_log": [],
            # ── New: phase timing ──
            "phase_start_times": {},
            "phase_durations": {},
            # ── New: retry history ──
            "retry_history": [],
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    def handle_event(self, event_type: str, data: dict) -> None:
        # Skip heartbeat — it's only for keeping the UI alive
        if event_type == "heartbeat":
            return

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
        }.get(event_type)

        if handler:
            handler(data)

        st.session_state["agent_steps"].append((event_type, data))

        # ── New: Append to event log with timestamp ──
        elapsed = 0.0
        started_at = st.session_state.get("started_at")
        if started_at:
            elapsed = time.time() - started_at

        # Build a compact data summary for the log
        summary = _summarize_event(event_type, data)
        st.session_state["event_log"].append({
            "elapsed": elapsed,
            "event_type": event_type,
            "summary": summary,
            "data": data,
        })

    # ── Existing handlers (enhanced with timing) ──

    def _on_plan_start(self, data: dict) -> None:
        st.session_state["current_step"] = "planning"
        st.session_state["current_detail"] = "正在拆解研究问题..."
        st.session_state["research_plan"] = []
        st.session_state["started_at"] = time.time()
        st.session_state["event_log"] = []
        st.session_state["phase_durations"] = {}
        st.session_state["phase_start_times"] = {"decomposition": time.time()}
        st.session_state["retry_history"] = []

    def _on_plan_chunk(self, data: dict) -> None:
        st.session_state["research_plan"].append({
            "index": data.get("index", 0),
            "question": data.get("question", ""),
            "strategy": data.get("strategy", ""),
            "rationale": data.get("rationale", ""),
        })
        # End decomposition phase timing
        if "decomposition" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("decomposition")
            st.session_state.get("phase_durations", {})["disassembly"] = time.time() - start

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
        # Record retrieval phase start
        phase_key = f"retrieval_step_{step}"
        st.session_state.get("phase_start_times", {})[phase_key] = time.time()

    def _on_retrieval_result(self, data: dict) -> None:
        count = data.get("result_count", 0)
        top = data.get("top_score", 0)
        preview = data.get("top_preview", "")
        st.session_state["retrieval_progress"]["results"] = count
        st.session_state["retrieval_progress"]["top_score"] = top
        # ── New: store top result preview ──
        st.session_state["retrieval_progress"]["top_preview"] = preview
        st.session_state["current_detail"] = f"检索完成，找到 {count} 条结果（最高相似度: {top:.2f})"
        # End retrieval phase timing
        phase_key = f"retrieval_step_{data.get('step', 0)}"
        if phase_key in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop(phase_key)
            st.session_state.get("phase_durations", {})[f"retrieval_step_{data.get('step', 0)}"] = time.time() - start

    def _on_critique_start(self, data: dict) -> None:
        st.session_state["current_step"] = "evaluating"
        st.session_state["current_detail"] = "正在评估检索质量..."
        # Record critique phase start
        st.session_state.get("phase_start_times", {})["critique"] = time.time()

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
            # ── New: store reasoning and retry suggestion ──
            "reasoning": reasoning,
            "retry_suggestion": retry_suggestion,
        })
        status_text = "通过" if passed else "不通过"
        st.session_state["current_detail"] = f"质量评估: {score:.2f} 分 — {status_text}"
        # End critique phase timing
        if "critique" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("critique")
            st.session_state.get("phase_durations", {})["evaluation"] = time.time() - start

    def _on_retry_triggered(self, data: dict) -> None:
        count = data.get("count", 0)
        st.session_state["current_step"] = "retrying"
        st.session_state["current_detail"] = f"检索质量不达标，正在第 {count} 次重试（改写查询）..."
        # ── New: store retry history ──
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

    def _on_synthesis_start(self, data: dict) -> None:
        st.session_state["current_step"] = "synthesizing"
        st.session_state["current_detail"] = "正在聚合多源信息，生成研究报告..."
        st.session_state.get("phase_start_times", {})["synthesis"] = time.time()

    def _on_synthesis_chunk(self, data: dict) -> None:
        pass

    def _on_done(self, data: dict) -> None:
        st.session_state["current_step"] = "done"
        st.session_state["current_detail"] = f"研究完成，报告共 {data.get('report_length', 0)} 字符"
        # End synthesis phase timing
        if "synthesis" in st.session_state.get("phase_start_times", {}):
            start = st.session_state["phase_start_times"].pop("synthesis")
            st.session_state.get("phase_durations", {})["synthesis"] = time.time() - start

    def _on_error(self, data: dict) -> None:
        st.session_state["current_step"] = "error"
        st.session_state["current_detail"] = data.get("message", "发生错误")


# ──────────────────── Event summary helper ────────────────────


def _summarize_event(event_type: str, data: dict) -> str:
    """Build a compact one-line summary for an SSE event."""
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


# ──────────────────── Render functions ────────────────────


def _render_event_log():
    """Render the real-time SSE event log panel (collapsed by default)."""
    events = st.session_state.get("event_log", [])
    if not events:
        return

    with st.expander("📜 事件日志", expanded=False):
        # Build a compact table
        rows = []
        for evt in events:
            rows.append({
                "时间": f"{evt['elapsed']:.1f}s",
                "事件": evt["event_type"],
                "摘要": evt["summary"],
            })

        # Use a simple markdown table for wide compatibility
        lines = ["| 时间 | 事件 | 摘要 |", "|------|------|------|"]
        for r in rows[-50:]:  # Show last 50 events to avoid clutter
            lines.append(f"| {r['时间']} | `{r['事件']}` | {r['摘要']} |")
        st.markdown("\n".join(lines))

        # Allow clicking to view raw payload of any event
        with st.expander("查看完整事件数据", expanded=False):
            for i, evt in enumerate(events[-10:]):
                key = f"payload_{i}_{len(events)}"
                with st.expander(f"[{evt['elapsed']:.1f}s] {evt['event_type']}", expanded=False):
                    try:
                        st.json(evt["data"], key=key)
                    except Exception:
                        st.text(str(evt["data"])[:500])


def _render_timing_stats():
    """Render per-phase timing statistics (collapsed by default)."""
    durations = st.session_state.get("phase_durations", {})
    if not durations:
        return

    with st.expander("⏱ 阶段耗时", expanded=False):
        lines = []
        total_time = 0.0
        label_map = {
            "disassembly": "拆解问题",
            "evaluation": "质量评估",
            "synthesis": "合成报告",
        }
        for key, dur in durations.items():
            label = label_map.get(key, key.replace("retrieval_step_", "检索步骤 "))
            lines.append(f"| {label} | {dur:.1f}s |")
            total_time += dur

        lines.insert(0, "| 阶段 | 耗时 |")
        lines.insert(1, "|------|------|")
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
                f"上次评分: {h['score']:.3f} | "
                f"建议: *{h.get('suggestion', 'N/A')}*"
            )


def render_progress_panel():
    """Render the agent progress visualization panel."""
    steps = st.session_state.get("agent_steps", [])
    current = st.session_state.get("current_step", "")
    detail = st.session_state.get("current_detail", "")
    plan = st.session_state.get("research_plan", [])
    critiques = st.session_state.get("critique_results", [])
    retry_count = st.session_state.get("retry_count", 0)
    retrieval = st.session_state.get("retrieval_progress", {})

    # ── Phase timeline ──
    phases = [
        ("decomposition", "planning", "📋 拆解问题"),
        ("retrieval", "retrieving", "🔍 检索"),
        ("critique", "evaluating", "✅ 评估"),
        ("synthesis", "synthesizing", "📝 合成报告"),
    ]

    current_phase_idx = -1
    for i, (_, key, _) in enumerate(phases):
        if current == key:
            current_phase_idx = i
            break

    cols = st.columns(len(phases))
    for i, (_, key, label) in enumerate(phases):
        with cols[i]:
            if i < current_phase_idx:
                st.markdown(f"~~{label}~~ ✅")
            elif i == current_phase_idx:
                if current == "retrying":
                    st.markdown(f"**{label}** 🔄")
                else:
                    spinner = "⏳" if current not in ("done", "error") else ""
                    st.markdown(f"**{label}** {spinner}")
            else:
                st.markdown(f"*{label}*")

    st.divider()

    # ── Current status ──
    if detail:
        if current == "error":
            st.error(f"**当前状态**: {detail}")
        elif current == "retrying":
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

    # ── Enhanced: Per-step detail ──
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
            st.markdown(f"**结果数**: {results} | **最高相似度**: {top_score:.3f}")
            if preview:
                key = f"preview_{step}_{total}"
                with st.expander("最佳结果预览", expanded=False):
                    st.text(preview)

    # ── Enhanced: Critique per-step ──
    if critiques:
        with st.expander("✅ 检索质量详情", expanded=False):
            for c in critiques:
                status_icon = "✅" if c["passed"] else "⚠️"
                st.markdown(
                    f"{status_icon} **步骤 {c['step']}**: "
                    f"综合 {c['score']:.2f} "
                    f"(相关性 {c.get('relevance', 0):.2f} / 完整性 {c.get('completeness', 0):.2f})"
                )
                # Show reasoning text
                reasoning = c.get("reasoning", "")
                if reasoning:
                    key = f"reasoning_{c['step']}_{len(critiques)}"
                    with st.expander(f"评分推理 (步骤 {c['step']})", expanded=False):
                        st.text(reasoning)
                # Show retry suggestion for failed critiques
                retry_sug = c.get("retry_suggestion", "")
                if not c["passed"] and retry_sug:
                    st.caption(f"💡 重试建议: *{retry_sug}*")

    # ── New: Retry history ──
    _render_retry_history()

    # ── New: Timing stats ──
    _render_timing_stats()

    # ── New: Event log ──
    _render_event_log()

    # ── Elapsed time ──
    started_at = st.session_state.get("started_at")
    if started_at and current not in ("done", "error", ""):
        elapsed = time.time() - started_at
        st.caption(f"⏱ 已用时: {elapsed:.0f} 秒")

    # ── Spinner while running ──
    if current not in ("done", "error", ""):
        if retrieval:
            step = retrieval.get("step", 0)
            total = retrieval.get("total", 0)
            if total > 0:
                step_progress = (step - 1 + (1 if current in ("evaluating",) else 0.5)) / total
                st.progress(min(max(step_progress, 0.05), 0.95), text="Agent 思考中...")
            else:
                st.progress(0.3, text="Agent 思考中...")
        else:
            st.progress(0.1, text="Agent 思考中...")
