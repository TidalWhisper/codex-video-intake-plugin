from __future__ import annotations

from typing import Any


RISK_TAG_HINTS: dict[str, tuple[str, ...]] = {
    "missing_character_reference": (),
    "storefront_branding": (
        "convenience store",
        "storefront",
        "store sign",
        "shop sign",
        "glass door",
        "灯牌",
        "店招",
        "玻璃门",
        "便利店",
    ),
    "umbrella_prop_contact": (
        "umbrella",
        "oil-paper umbrella",
        "paper umbrella",
        "parasol",
        "伞",
        "油纸伞",
    ),
    "weapon_hand_contact": (
        "sword",
        "katana",
        "saber",
        "rapier",
        "blade",
        "longsword",
        "剑",
        "刀",
    ),
    "fan_hand_contact": (
        "folding fan",
        "hand fan",
        "paper fan",
        "折扇",
        "团扇",
        "扇子",
    ),
    "instrument_hand_contact": (
        "flute",
        "bamboo flute",
        "dizi",
        "xiao",
        "笛子",
        "长笛",
        "竹笛",
        "箫",
    ),
    "cup_hand_contact": (
        "teacup",
        "tea cup",
        "cup of tea",
        "wine glass",
        "goblet",
        "茶杯",
        "酒杯",
        "杯盏",
        "杯子",
    ),
    "two_subject_contact": (
        "holding hands",
        "hold hands",
        "handshake",
        "embracing",
        "embrace each other",
        "hugging each other",
        "牵手",
        "握手",
        "相拥",
        "拥抱",
    ),
    "riding_pose_contact": (
        "riding a bicycle",
        "riding bicycle",
        "on a bicycle",
        "riding a horse",
        "riding horse",
        "riding the horse",
        "horseback",
        "riding motorcycle",
        "骑自行车",
        "骑马",
        "骑摩托",
    ),
}

RISK_TAG_REASONS: dict[str, str] = {
    "missing_character_reference": "Character-locked continuity is required, but no Stage 03 reference image is available for this shot. Start/end keyframes can drift into different people before Stage 06.",
    "storefront_branding": "Convenience-store storefront scenes can still hallucinate chain-sign identity marks even when the prompt says no branding. Review signage and facade treatment carefully before Stage 06.",
    "umbrella_prop_contact": "Umbrella prop-contact scenes generated without structure guidance are still prone to anatomy drift, handle-contact errors, and duplicate umbrella artifacts. Review carefully before Stage 06.",
    "weapon_hand_contact": "Weapon-hand contact scenes generated without structure guidance are still prone to grip realism issues, limb-count errors, and blade-hand alignment drift. Review carefully before Stage 06.",
    "fan_hand_contact": "Hand-fan scenes generated without structure guidance are still prone to finger-count errors, wrist articulation drift, and fan-handle contact failures. Review carefully before Stage 06.",
    "instrument_hand_contact": "Instrument-contact scenes generated without structure guidance are still prone to incorrect hand placement, mouth alignment drift, and duplicate prop artifacts. Review carefully before Stage 06.",
    "cup_hand_contact": "Cup or goblet hand-contact scenes generated without structure guidance are still prone to finger articulation drift, cup orientation errors, and liquid-container contact failures. Review carefully before Stage 06.",
    "two_subject_contact": "Two-subject contact scenes generated without structure guidance are still prone to hand-join drift, overlapping-limb errors, and duplicated body parts. Review carefully before Stage 06.",
    "riding_pose_contact": "Riding scenes generated without structure guidance are still prone to seat-contact drift, limb-orientation errors, and vehicle or mount alignment failures. Review carefully before Stage 06.",
}

RISK_TAG_CREATOR_SUMMARY: dict[str, str] = {
    "missing_character_reference": "这类镜头缺少角色参考图，最容易出现前后关键帧直接换人。",
    "storefront_branding": "这类便利店镜头最容易偷偷长出连锁店招、三色横条和可读品牌字样。",
    "umbrella_prop_contact": "这类镜头最容易出现多手、双伞、握伞关系漂移。",
    "weapon_hand_contact": "这类镜头最容易出现持械手型错误、手臂数量异常、刀柄贴合不自然。",
    "fan_hand_contact": "这类镜头最容易出现扇柄握持不自然、手指数量错误、扇面重复。",
    "instrument_hand_contact": "这类镜头最容易出现手位错误、嘴部对位错误、道具重复。",
    "cup_hand_contact": "这类镜头最容易出现杯子数量错误、杯口朝向错误、手指穿模。",
    "two_subject_contact": "这类镜头最容易出现牵手关系断裂、肢体重叠错误、人物重复。",
    "riding_pose_contact": "这类镜头最容易出现骑乘接触点错误、四肢方向异常、载具贴合失真。",
}

RISK_TAG_REPAIR_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "missing_character_reference": (
        "先补一张主角参考图，或把同一人物的脸型、发型、服装、包和主道具写成固定 identity anchor。",
        "明确 primary protagonist remains the same person in every frame，secondary人物不能抢成主角。",
        "如果必须先跑无参考图版本，至少逐张对比 start / mid / end，确认是不是同一个人再进 Stage 06。",
    ),
    "storefront_branding": (
        "把便利店外立面改成无字、无商标、无三色连锁横条的普通暖色灯箱，不要让人一眼联想到真实连锁品牌。",
        "明确禁止红黄绿三色横条、蓝白红横条、可读罗马字母招牌和任何标准化连锁便利店顶招。",
        "如果镜头只需要暖光来源，就把招牌弱化成模糊暖白发光面，不要让店招本身成为视觉主体。",
        "优先让暖光从玻璃门和室内溢出，不要把完整顶部门头、亮白长灯箱和上方深色字样一起摆成正面门头结构；必要时直接裁掉或虚化顶招区域。",
        "玻璃门上的红绿橙门贴、彩色腰线和窗贴海报也要一起去掉，只保留干净玻璃或低对比度中性色磨砂提示条。",
        "入口玻璃上的彩色促销海报、价签板和贴纸面板也不要留下；如果必须有提示信息，只允许极小、低对比度、不可读的中性提示块。",
    ),
    "umbrella_prop_contact": (
        "强调 single subject, one umbrella only, exactly two hands visible。",
        "明确 umbrella handle stays in one believable hand, no second umbrella, no extra fingers。",
        "减少大幅挥手动作，优先半身或中景构图，降低手部暴露面积。",
    ),
    "weapon_hand_contact": (
        "强调 exactly one weapon, exactly two hands, realistic grip on the handle。",
        "减少夸张挥砍动作，先保证握柄贴合和肘腕走向正确。",
        "避免遮挡过重的近景，优先能看清手与武器连接关系的构图。",
    ),
    "fan_hand_contact": (
        "强调 one fan only, five fingers per visible hand, natural wrist articulation。",
        "固定扇柄接触点，避免扇面重复或悬浮。",
        "优先胸像或半身构图，减少复杂交叉手势。",
    ),
    "instrument_hand_contact": (
        "强调 one instrument only, believable finger placement, no duplicated prop。",
        "明确 mouth alignment and hand position stay anatomically plausible。",
        "减少强透视近景，优先稳定中景。",
    ),
    "cup_hand_contact": (
        "强调 one cup only, natural finger wrap, stable cup orientation。",
        "避免液体容器同时靠近多只手，固定主握持手。",
        "优先桌面支撑或托盘辅助，降低悬空握持难度。",
    ),
    "two_subject_contact": (
        "强调 exactly two subjects, one clear hand connection, no extra arms or mirrored hands。",
        "减少肢体交叠角度，优先轮廓清楚的并排或轻接触构图。",
        "明确谁主动接触、接触点在哪只手。",
    ),
    "riding_pose_contact": (
        "强调 believable seat contact, aligned hips, correct limb orientation。",
        "减少腾空或极端动态，先保证人物和坐骑/载具贴合。",
        "固定 reins/handlebars/seat contact points，避免悬浮四肢。",
    ),
}

RISK_TAG_REPAIR_PROMPT_SECTIONS: dict[str, tuple[str, ...]] = {
    "missing_character_reference": (
        "Repair priority: keep the same protagonist face shape, hairstyle, outfit silhouette, body proportions, and carried accessories across all frames.",
        "Identity correction: primary protagonist remains the same person in every frame; secondary subjects must not replace or visually overpower the protagonist.",
    ),
    "storefront_branding": (
        "Repair priority: storefront facade must stay generic and unbranded, with no readable shop name, no logo, no chain-store color band, and no familiar convenience-store sign system.",
        "Sign correction: if a sign is visible, keep it as a plain warm light box or diffuse glow only, with no red-yellow-green tricolor stripe, no blue-white-red stripe, and no roman-letter store header.",
        "Composition correction: favor warm interior spill through the glass doors, and crop or blur the upper storefront fascia so no bright marquee panel or dark header lettering reads like a full chain-store facade.",
        "Door/glass correction: keep entrance glass plain or with only a subtle neutral frosted safety band, with no tri-color door decal, no colored glass-door stripe, and no chain-store window sticker band.",
        "Poster correction: remove colorful promo posters, sale-card panels, and branded sticker blocks from the entrance glass; any remaining notice must stay tiny, neutral, and unreadable.",
    ),
    "umbrella_prop_contact": (
        "Repair priority: single subject only, one umbrella only, exactly two arms and two hands, natural umbrella-handle grip, no duplicate canopy, no floating umbrella.",
        "Composition correction: keep the umbrella contact clearly readable and avoid extra background umbrellas or mirrored accessories.",
    ),
    "weapon_hand_contact": (
        "Repair priority: one weapon only, exactly two arms and two hands, realistic handle grip, no duplicated blade, no floating weapon.",
        "Composition correction: keep the hand-to-handle connection clearly visible and avoid broken wrist angles.",
    ),
    "fan_hand_contact": (
        "Repair priority: one fan only, natural wrist articulation, five fingers per visible hand, no duplicated fan surface.",
        "Composition correction: keep the fan-handle contact readable and avoid overlapping hands.",
    ),
    "instrument_hand_contact": (
        "Repair priority: one instrument only, believable hand placement, stable mouth alignment, no duplicate instrument.",
        "Composition correction: keep the instrument contact readable and avoid extra hands.",
    ),
    "cup_hand_contact": (
        "Repair priority: one cup only, natural finger wrap, correct cup orientation, no duplicate cup, no extra fingers.",
        "Composition correction: keep the cup-hand contact readable and avoid impossible grip.",
    ),
    "two_subject_contact": (
        "Repair priority: exactly two subjects, one clear contact point, no extra arms, no mirrored hands, no duplicated body parts.",
        "Composition correction: separate body silhouettes so the hand connection remains readable.",
    ),
    "riding_pose_contact": (
        "Repair priority: believable riding pose, clear seat contact, aligned hips and knees, no floating limbs, no duplicate mount parts.",
        "Composition correction: keep rider-to-mount contact readable and avoid extreme distortion.",
    ),
}

RISK_TAG_REPAIR_NEGATIVE_HINTS: dict[str, tuple[str, ...]] = {
    "missing_character_reference": ("different face", "different hairstyle", "different outfit", "changed body shape", "identity swap"),
    "storefront_branding": (
        "readable storefront wordmark",
        "chain convenience store signage",
        "red yellow green tricolor fascia",
        "blue white red store stripe",
        "branded convenience facade",
        "backlit rectangular storefront marquee",
        "dark header lettering above light box",
        "full storefront top fascia",
        "tri-color door decal",
        "colored glass-door stripe",
        "chain-store window sticker band",
        "colorful promo poster on glass door",
        "sale card panel on entrance glass",
    ),
    "umbrella_prop_contact": ("extra hands", "extra umbrella", "duplicate umbrella canopy", "floating umbrella", "broken grip"),
    "weapon_hand_contact": ("extra weapon", "duplicate blade", "floating sword", "broken wrist", "extra fingers"),
    "fan_hand_contact": ("duplicate fan", "extra fingers", "broken wrist", "floating fan"),
    "instrument_hand_contact": ("duplicate instrument", "extra fingers", "floating flute", "mouth misalignment"),
    "cup_hand_contact": ("duplicate cup", "spilled impossible liquid", "extra fingers", "floating cup"),
    "two_subject_contact": ("extra arms", "extra hands", "merged torsos", "duplicated limbs"),
    "riding_pose_contact": ("floating rider", "broken legs", "duplicate reins", "misaligned saddle contact"),
}

RISK_TAG_REVIEW_CHECKLIST: dict[str, tuple[str, ...]] = {
    "missing_character_reference": (
        "把 start / mid / end 三张图并排看，确认是不是同一个主角，不要只看单张是否好看。",
        "确认脸型、发型、服装轮廓、包和主道具关系跨帧一致，没有突然换人或换装。",
        "如果画面里有第二个人，确认主角仍然是同一人，不能让陌生人抢成主角。",
    ),
    "storefront_branding": (
        "先看店外立面或店内顶部有没有可读品牌字样、店招词头或明显 logo。",
        "再看有没有红黄绿三色横条、蓝白红横条或一眼能联想到真实连锁便利店的标准化配色。",
        "如果镜头只需要暖光氛围，确认店招已经退成无字灯箱或模糊光面，而不是画面主视觉。",
    ),
    "umbrella_prop_contact": (
        "确认画面里只有一把伞，没有重复伞面或背景多出第二把伞。",
        "确认主体只有两只手，且没有多余手指、额外手臂或镜像肢体。",
        "确认握伞手和伞柄贴合自然，没有悬浮、穿模或断开。",
    ),
    "weapon_hand_contact": (
        "确认画面里只有一把武器，没有重复刀身或漂浮武器。",
        "确认持械手只有正常数量的手指和手臂，没有断腕或反关节。",
        "确认刀柄与手掌贴合自然，挥动方向和肘腕走向合理。",
    ),
    "fan_hand_contact": (
        "确认画面里只有一把扇子，没有重复扇面或漂浮扇柄。",
        "确认可见手指数量正确，手腕角度自然。",
        "确认扇柄接触点清楚，不要出现手指穿扇或握柄断开。",
    ),
    "instrument_hand_contact": (
        "确认画面里只有一个乐器，没有复制或悬浮。",
        "确认手位真实，手指没有穿模或数量异常。",
        "确认嘴部、手位和乐器方向匹配，不要出现吹奏关系错位。",
    ),
    "cup_hand_contact": (
        "确认画面里只有一个杯子，没有重复杯体或漂浮容器。",
        "确认主握持手自然包裹杯身，没有额外手指。",
        "确认杯口朝向和液体重力关系合理，不要出现不可能的倾斜。",
    ),
    "two_subject_contact": (
        "确认只有两个人物主体，没有重影或多出肢体。",
        "确认接触点只有一个明确关系，手和手没有错位断裂。",
        "确认人物轮廓分离清楚，不要出现胳膊互相穿插。",
    ),
    "riding_pose_contact": (
        "确认人物与坐骑或载具接触自然，没有悬空坐姿。",
        "确认双腿、髋部和膝盖朝向合理，没有反折或断裂。",
        "确认缰绳、车把或座位接触点清楚，没有多余部件。",
    ),
}

RISK_TAG_REVIEW_FOCUS: dict[str, str] = {
    "missing_character_reference": "先横向比对 start / mid / end 是不是同一个人，再看发型、服装和主道具有没有跨帧漂移。",
    "storefront_branding": "先查有没有可读店招，再查有没有连锁便利店标准配色横条，最后确认暖光是否只是氛围而不是品牌露出。",
    "umbrella_prop_contact": "先查伞的数量，再查手的数量，最后查握伞手和伞柄是否贴合。",
    "weapon_hand_contact": "先查武器是否重复，再查持械手型，最后查刀柄贴合。",
    "fan_hand_contact": "先查扇面是否重复，再查手指数量，最后查扇柄接触。",
    "instrument_hand_contact": "先查乐器是否重复，再查手位，最后查嘴部和乐器对位。",
    "cup_hand_contact": "先查杯子数量，再查主握持手，最后查杯口方向。",
    "two_subject_contact": "先查人物数量，再查接触点，再查轮廓是否互相穿插。",
    "riding_pose_contact": "先查坐姿是否贴合，再查四肢朝向，最后查控制点接触。",
}

RISK_TAG_PRIORITY_SCORES: dict[str, int] = {
    "missing_character_reference": 98,
    "storefront_branding": 88,
    "umbrella_prop_contact": 96,
    "weapon_hand_contact": 93,
    "two_subject_contact": 91,
    "riding_pose_contact": 89,
    "instrument_hand_contact": 85,
    "fan_hand_contact": 83,
    "cup_hand_contact": 80,
}

UMBRELLA_HINTS = RISK_TAG_HINTS["umbrella_prop_contact"]

PROMPT_ONLY_CONTROL_MODES = {"", "prompt_only", "text_only"}
STRUCTURE_GUIDED_CONTROL_MODES = {"pose_guided", "reference_guided", "controlnet_guided"}
MANUAL_REVIEW_CLEAR_STATES = {"approved", "waived", "not_required"}
ALWAYS_MANUAL_REVIEW_ROUTE_HINTS = {"interaction_handoff"}
ALWAYS_MANUAL_REVIEW_RISK_TAGS = {"storefront_branding"}
REFERENCE_GUIDED_AUTO_REPAIR_RISK_TAGS = {"storefront_branding"}
MANUAL_REVIEW_APPROVED_STATES = {"approved", "waived"}


def _is_codex_contract_job(job: dict[str, Any], gate: dict[str, Any] | None = None) -> bool:
    sources = [
        str(job.get("semantic_source") or "").strip().lower(),
        str(job.get("stage05_semantic_source") or "").strip().lower(),
    ]
    if isinstance(gate, dict):
        sources.append(str(gate.get("semantic_source") or "").strip().lower())
    return any(source == "codex_contract" for source in sources)


def _joined_job_text(job: dict[str, Any]) -> str:
    return " ".join(
        str(job.get(key) or "")
        for key in [
            "prompt",
            "style_prompt",
            "consistency_prompt",
            "camera_prompt",
            "negative_prompt",
        ]
    ).lower()


def scene_risk_tags_for_job(job: dict[str, Any]) -> list[str]:
    joined = _joined_job_text(job)
    tags: list[str] = []
    for tag, hints in RISK_TAG_HINTS.items():
        if not hints:
            continue
        if any(hint.lower() in joined for hint in hints):
            tags.append(tag)
    return tags


def metadata_risk_tags_for_job(job: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    missing_reference_images = job.get("missing_reference_images")
    route_hint = str(job.get("stage06_route_hint") or "").strip().lower()
    joined = _joined_job_text(job)
    if (
        isinstance(missing_reference_images, list)
        and any(str(item or "").strip() for item in missing_reference_images)
        and (job.get("stage06_requires_mid_guide") is True or route_hint == "interaction_handoff")
    ):
        tags.append("missing_character_reference")
    storefront_cues = ("convenience store", "storefront", "店招", "便利店", "glass door", "玻璃门")
    brand_guardrail_cues = ("brand", "logo", "wordmark", "商标", "无品牌")
    if any(cue in joined for cue in storefront_cues) and any(cue in joined for cue in brand_guardrail_cues):
        tags.append("storefront_branding")
    return tags


def control_mode_for_job(job: dict[str, Any]) -> str:
    return str(job.get("comfyui_control_mode") or "prompt_only").strip().lower() or "prompt_only"


def auto_repair_enabled_for_gate(*, risk_tags: list[str], control_mode: str, route_hint: str) -> bool:
    return bool(risk_tags) and (
        control_mode in PROMPT_ONLY_CONTROL_MODES
        or route_hint in ALWAYS_MANUAL_REVIEW_ROUTE_HINTS
        or (
            control_mode in STRUCTURE_GUIDED_CONTROL_MODES
            and any(tag in REFERENCE_GUIDED_AUTO_REPAIR_RISK_TAGS for tag in risk_tags)
        )
    )


def manual_review_reason_for_tags(risk_tags: list[str], *, control_mode: str) -> str | None:
    if not risk_tags:
        return None
    if control_mode in PROMPT_ONLY_CONTROL_MODES:
        for tag in risk_tags:
            reason = RISK_TAG_REASONS.get(tag)
            if reason:
                return reason
    return None


def creator_risk_summary_for_tags(risk_tags: list[str]) -> str | None:
    summaries = [RISK_TAG_CREATOR_SUMMARY[tag] for tag in risk_tags if tag in RISK_TAG_CREATOR_SUMMARY]
    if not summaries:
        return None
    unique: list[str] = []
    for item in summaries:
        if item not in unique:
            unique.append(item)
    return " ".join(unique)


def creator_repair_suggestions_for_tags(risk_tags: list[str]) -> list[str]:
    suggestions: list[str] = []
    seen: set[str] = set()
    for tag in risk_tags:
        for item in RISK_TAG_REPAIR_SUGGESTIONS.get(tag, ()):
            if item not in seen:
                suggestions.append(item)
                seen.add(item)
    return suggestions


def repair_prompt_sections_for_tags(risk_tags: list[str]) -> list[str]:
    sections: list[str] = []
    seen: set[str] = set()
    for tag in risk_tags:
        for item in RISK_TAG_REPAIR_PROMPT_SECTIONS.get(tag, ()):
            if item not in seen:
                sections.append(item)
                seen.add(item)
    return sections


def repair_negative_hints_for_tags(risk_tags: list[str]) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for tag in risk_tags:
        for item in RISK_TAG_REPAIR_NEGATIVE_HINTS.get(tag, ()):
            lowered = item.lower()
            if lowered not in seen:
                hints.append(item)
                seen.add(lowered)
    return hints


def review_checklist_for_tags(risk_tags: list[str]) -> list[str]:
    checklist: list[str] = []
    seen: set[str] = set()
    for tag in risk_tags:
        for item in RISK_TAG_REVIEW_CHECKLIST.get(tag, ()):
            if item not in seen:
                checklist.append(item)
                seen.add(item)
    return checklist


def review_focus_for_tags(risk_tags: list[str]) -> str | None:
    focuses = [RISK_TAG_REVIEW_FOCUS[tag] for tag in risk_tags if tag in RISK_TAG_REVIEW_FOCUS]
    if not focuses:
        return None
    unique: list[str] = []
    for item in focuses:
        if item not in unique:
            unique.append(item)
    return " ".join(unique)


def review_priority_for_tags(risk_tags: list[str]) -> dict[str, Any]:
    unique_tags = [tag for tag in risk_tags if tag]
    if not unique_tags:
        return {
            "score": 0,
            "label": "无需复核",
            "bucket": "none",
        }
    base_score = max(RISK_TAG_PRIORITY_SCORES.get(tag, 75) for tag in unique_tags)
    score = min(99, base_score + max(0, len(set(unique_tags)) - 1) * 2)
    if score >= 90:
        label = "高优先级复核"
        bucket = "high"
    elif score >= 82:
        label = "中优先级复核"
        bucket = "medium"
    else:
        label = "常规复核"
        bucket = "normal"
    return {
        "score": score,
        "label": label,
        "bucket": bucket,
    }


def build_quality_gate(job: dict[str, Any]) -> dict[str, Any]:
    existing = job.get("quality_gate")
    gate = dict(existing) if isinstance(existing, dict) else {}
    is_codex_contract = _is_codex_contract_job(job, gate)
    seed_tags = gate.get("risk_tags") if isinstance(gate.get("risk_tags"), list) else (scene_risk_tags_for_job(job) + metadata_risk_tags_for_job(job))
    risk_tags = [str(tag).strip() for tag in seed_tags if str(tag).strip()]
    control_mode = str(gate.get("control_mode") or control_mode_for_job(job)).strip().lower() or "prompt_only"
    route_hint = str(job.get("stage06_route_hint") or "").strip().lower()
    if is_codex_contract and "requires_manual_review" in gate:
        requires_manual_review = bool(gate.get("requires_manual_review"))
    else:
        requires_manual_review = bool(risk_tags) and (
            control_mode not in STRUCTURE_GUIDED_CONTROL_MODES
            or route_hint in ALWAYS_MANUAL_REVIEW_ROUTE_HINTS
            or any(tag in ALWAYS_MANUAL_REVIEW_RISK_TAGS for tag in risk_tags)
        )
    review_status = str(gate.get("manual_review_status") or "").strip().lower()
    if requires_manual_review:
        if not (is_codex_contract and review_status):
            if review_status not in MANUAL_REVIEW_APPROVED_STATES:
                review_status = "pending"
    else:
        review_status = "not_required"
    gate["risk_tags"] = risk_tags
    gate["control_mode"] = control_mode
    gate["requires_manual_review"] = requires_manual_review
    gate["manual_review_status"] = review_status
    gate["semantic_source"] = str(gate.get("semantic_source") or job.get("semantic_source") or "").strip() or None
    gate["reason"] = str(gate.get("reason") or manual_review_reason_for_tags(risk_tags, control_mode=control_mode) or "").strip() or None
    gate["creator_risk_summary"] = (
        str(gate.get("creator_risk_summary") or creator_risk_summary_for_tags(risk_tags) or "").strip() or None
    )
    gate["creator_repair_suggestions"] = (
        gate.get("creator_repair_suggestions")
        if isinstance(gate.get("creator_repair_suggestions"), list)
        else creator_repair_suggestions_for_tags(risk_tags)
    )
    priority = review_priority_for_tags(risk_tags)
    gate["review_priority_score"] = int(gate.get("review_priority_score") or priority["score"])
    gate["review_priority_label"] = str(gate.get("review_priority_label") or priority["label"])
    gate["review_priority_bucket"] = str(gate.get("review_priority_bucket") or priority["bucket"])
    gate["review_checklist"] = (
        gate.get("review_checklist")
        if isinstance(gate.get("review_checklist"), list)
        else review_checklist_for_tags(risk_tags)
    )
    gate["review_focus"] = str(gate.get("review_focus") or review_focus_for_tags(risk_tags) or "").strip() or None
    if is_codex_contract and "auto_repair_recommended" in gate:
        gate["auto_repair_recommended"] = bool(gate.get("auto_repair_recommended"))
    else:
        gate["auto_repair_recommended"] = auto_repair_enabled_for_gate(
            risk_tags=risk_tags,
            control_mode=control_mode,
            route_hint=route_hint,
        )
    return gate


def quality_gate_is_cleared(gate: dict[str, Any]) -> bool:
    return str(gate.get("manual_review_status") or "").strip().lower() in MANUAL_REVIEW_CLEAR_STATES


def build_auto_repair_plan(job: dict[str, Any], gate: dict[str, Any] | None = None) -> dict[str, Any]:
    explicit_plan = job.get("auto_repair_plan")
    if _is_codex_contract_job(job, gate) and isinstance(explicit_plan, dict):
        return dict(explicit_plan)
    if isinstance(gate, dict):
        normalized_job = dict(job)
        normalized_job["quality_gate"] = gate
        gate = build_quality_gate(normalized_job)
    else:
        gate = build_quality_gate(job)
    risk_tags = [str(tag).strip() for tag in (gate.get("risk_tags") or []) if str(tag).strip()]
    route_hint = str(job.get("stage06_route_hint") or "").strip().lower()
    control_mode = str(gate.get("control_mode") or "").strip().lower()
    enabled = auto_repair_enabled_for_gate(
        risk_tags=risk_tags,
        control_mode=control_mode,
        route_hint=route_hint,
    )
    reference_guided_repair = (
        enabled
        and control_mode in STRUCTURE_GUIDED_CONTROL_MODES
        and (
            route_hint in ALWAYS_MANUAL_REVIEW_ROUTE_HINTS
            or any(tag in REFERENCE_GUIDED_AUTO_REPAIR_RISK_TAGS for tag in risk_tags)
        )
    )
    return {
        "enabled": enabled,
        "mode": (
            "two_pass_reference_guided_repair"
            if reference_guided_repair
            else "two_pass_prompt_repair"
            if enabled
            else "none"
        ),
        "target_failure_modes": risk_tags,
        "reason": gate.get("reason"),
        "creator_summary": gate.get("creator_risk_summary"),
        "creator_repair_suggestions": list(gate.get("creator_repair_suggestions") or []),
        "repair_prompt_sections": repair_prompt_sections_for_tags(risk_tags),
        "repair_negative_hints": repair_negative_hints_for_tags(risk_tags),
        "pass_count": 2 if enabled else 1,
    }


def build_creator_review_card(
    job: dict[str, Any],
    gate: dict[str, Any] | None = None,
    *,
    auto_repair_status: str | None = None,
) -> dict[str, Any] | None:
    explicit_card = job.get("creator_review_card")
    if _is_codex_contract_job(job, gate) and isinstance(explicit_card, dict):
        card = dict(explicit_card)
        if auto_repair_status and "auto_repair_status" not in card:
            card["auto_repair_status"] = auto_repair_status
        return card
    if isinstance(gate, dict):
        normalized_job = dict(job)
        normalized_job["quality_gate"] = gate
        gate = build_quality_gate(normalized_job)
    else:
        gate = build_quality_gate(job)
    risk_tags = [str(tag).strip() for tag in (gate.get("risk_tags") or []) if str(tag).strip()]
    if not risk_tags:
        return None
    card = {
        "headline": gate.get("creator_risk_summary"),
        "priority_label": gate.get("review_priority_label"),
        "priority_score": gate.get("review_priority_score"),
        "focus": gate.get("review_focus"),
        "checklist": list(gate.get("review_checklist") or []),
        "suggestions": list(gate.get("creator_repair_suggestions") or [])[:3],
        "next_step": "先按复核清单逐项检查；任一项不通过时，优先按建议回改 prompt 后重生。",
    }
    if auto_repair_status:
        card["auto_repair_status"] = auto_repair_status
    return card


def summarize_quality_review(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    risky_image_ids: list[str] = []
    blocking_image_ids: list[str] = []
    required_count = 0
    approved_count = 0
    pending_count = 0
    waived_count = 0
    review_queue: list[dict[str, Any]] = []
    for job in jobs:
        gate = build_quality_gate(job)
        job["quality_gate"] = gate
        image_id = str(job.get("image_id") or "").strip()
        status = str(gate.get("manual_review_status") or "").strip().lower()
        if gate["risk_tags"] and image_id:
            risky_image_ids.append(image_id)
            if gate["requires_manual_review"] and status not in MANUAL_REVIEW_CLEAR_STATES:
                review_queue.append({
                    "image_id": image_id,
                    "shot_id": str(job.get("shot_id") or "").strip() or None,
                    "frame_role": str(job.get("frame_role") or "").strip() or None,
                    "priority_label": gate.get("review_priority_label"),
                    "priority_score": gate.get("review_priority_score"),
                    "review_focus": gate.get("review_focus"),
                    "checklist": list(gate.get("review_checklist") or [])[:3],
                    "risk_summary": gate.get("creator_risk_summary"),
                    "suggestions": list(gate.get("creator_repair_suggestions") or [])[:3],
                    "manual_review_status": gate.get("manual_review_status"),
                    "auto_repair_status": job.get("auto_repair_status"),
                })
        if gate["requires_manual_review"]:
            required_count += 1
            if status == "approved":
                approved_count += 1
            elif status == "waived":
                waived_count += 1
            elif image_id:
                pending_count += 1
                blocking_image_ids.append(image_id)
    manual_review_cleared = pending_count == 0
    frame_role_order = {"start": 0, "mid": 1, "end": 2}
    review_queue.sort(
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            str(item.get("shot_id") or ""),
            frame_role_order.get(str(item.get("frame_role") or "").strip().lower(), 99),
            str(item.get("image_id") or ""),
        )
    )
    next_review_image_ids = [str(item["image_id"]) for item in review_queue[:3] if item.get("image_id")]
    top_review_cards = [
        {
            "rank": index + 1,
            "image_id": str(item.get("image_id") or ""),
            "shot_id": item.get("shot_id"),
            "frame_role": item.get("frame_role"),
            "priority_label": item.get("priority_label"),
            "priority_score": item.get("priority_score"),
            "headline": item.get("risk_summary"),
            "first_check": item.get("review_focus"),
            "quick_fix": (item.get("suggestions") or [None])[0],
            "manual_review_status": item.get("manual_review_status"),
            "auto_repair_status": item.get("auto_repair_status"),
        }
        for index, item in enumerate(review_queue[:3])
    ]
    return {
        "risky_image_count": len(risky_image_ids),
        "risky_image_ids": risky_image_ids,
        "required_count": required_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "waived_count": waived_count,
        "blocking_image_ids": blocking_image_ids,
        "manual_review_cleared": manual_review_cleared,
        "review_queue": review_queue,
        "next_review_image_ids": next_review_image_ids,
        "top_review_cards": top_review_cards,
        "creator_feedback_headline": (
            "高风险镜头已进入人工复核队列，请优先检查手部、道具数量和握持关系。"
            if pending_count
            else "高风险镜头已完成人工复核，可继续进入下一阶段。"
            if risky_image_ids
            else "当前关键帧未命中高风险接触类镜头。"
        ),
    }
