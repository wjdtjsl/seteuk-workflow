#!/usr/bin/env python3
"""
check_seteuk.py

세특(교과세부능력 및 특기사항) 초안이 기계적으로 확인 가능한 규정을 지켰는지 점검한다.
서사 구조, 관찰 시점의 진정성, 어휘 다양성 같은 질적 판단은 이 스크립트가 대신하지 못한다.
그런 부분은 사람 혹은 Claude가 직접 다시 읽고 판단해야 한다. 이 스크립트는 사람이 매번
눈으로 글자 수를 세거나 금지어를 찾는 실수를 줄이기 위한 보조 도구다.

사용법:
    python3 check_seteuk.py "세특 문단 전체 텍스트"
    python3 check_seteuk.py --file draft.txt
    python3 check_seteuk.py --file draft.txt --target 450
"""

import argparse
import re
import sys


# 가운데 점으로 흔히 쓰이는 문자들 (일반 가운데점, 한글 자모 아래아점, 불릿 등)
MIDDLE_DOTS = ["·", "‧", "ㆍ", "•", "∙"]

FULLWIDTH_PARENS = ["（", "）"]
HALFWIDTH_PARENS = ["(", ")"]

CURLY_QUOTES = ["“", "”", "‘", "’"]
STRAIGHT_DOUBLE_QUOTE = '"'

BANNED_WORDS = ["논문"]

# 사용자가 지정한 금지 표현과, 흔히 함께 쓰이는 활용형까지 넓게 잡는다.
VAGUE_PRAISE_PATTERNS = [
    r"우수(?:함|한|하다|하게|해)",
    r"뛰어나(?:다|게|서|며)?|뛰어난",
    r"탁월(?:함|한|하다|하게|해)",
]

# 책/작품 제목 뒤에 저자를 소괄호로 붙이는 것은 세특의 관용적 인용 표기이므로 예외로 둔다.
# 예: '난장이가 쏘아올린 작은 공(조세희)' 처럼 닫는 작은따옴표 바로 뒤에 오는 괄호만 예외.
CITATION_PAREN_RE = re.compile(r"'[^'\n]{1,80}\([^()\n]{1,40}\)'")

# 파일 끝에 별도 줄로 붙는 글자 수 표기를 인식해서 본문 분석에서 제외한다.
# 예: "(483자)", "(총 483자)", "글자 수: 483자", "483자"
TRAILING_COUNT_RE = re.compile(
    r"[\s\(（]*(?:총\s*)?(?:글자\s*수\s*[:：]?\s*)?\d+\s*자\s*[\)）]?\s*$"
)

# 종성 ㅁ(index 16)으로 끝나는지 확인해 명사형 종결어미(함/음/임/힘/삶/앎 등)를 넓게 잡는다.
HANGUL_BASE = 0xAC00
HANGUL_FINALS_PER_MEDIAL = 28
FINAL_MIEUM_INDEX = 16


def strip_trailing_char_count(text):
    """마지막 줄이 글자 수 표기라면 분리해서 (본문, 표기여부) 를 반환한다."""
    lines = text.strip().split("\n")
    if not lines:
        return text.strip(), False
    last = lines[-1].strip()
    if TRAILING_COUNT_RE.fullmatch(last) or re.fullmatch(r"[\(（]\s*\d+\s*자\s*[\)）]", last):
        body = "\n".join(lines[:-1]).strip()
        return body, True
    m = TRAILING_COUNT_RE.search(text.strip())
    if m and m.start() > 0:
        return text.strip()[: m.start()].strip(), True
    return text.strip(), False


def ends_with_mieum_batchim(text):
    """텍스트 끝(마침표 등 제외)이 종성 ㅁ 받침으로 끝나는 한글 음절인지 확인."""
    candidate = text.strip().rstrip(".!?~ \n\t")
    if not candidate:
        return False
    last_char = candidate[-1]
    code = ord(last_char)
    if not (HANGUL_BASE <= code <= 0xD7A3):
        return False
    offset = code - HANGUL_BASE
    final_index = offset % HANGUL_FINALS_PER_MEDIAL
    return final_index == FINAL_MIEUM_INDEX


def find_context_snippets(text, needles, window=6):
    hits = []
    for n in needles:
        start = 0
        while True:
            idx = text.find(n, start)
            if idx == -1:
                break
            lo = max(0, idx - window)
            hi = min(len(text), idx + len(n) + window)
            hits.append((n, text[lo:hi].replace("\n", " ")))
            start = idx + 1
    return hits


def check(text, target_chars=500, tolerance=0.15):
    issues = []
    warnings = []

    body, had_count_annotation = strip_trailing_char_count(text)
    char_count = len(body)

    low = target_chars * (1 - tolerance)
    high = target_chars * (1 + tolerance)
    if not (low <= char_count <= high):
        issues.append(
            f"글자 수 {char_count}자가 목표 {target_chars}자 기준 허용 범위"
            f"({int(low)}~{int(high)}자)를 벗어남"
        )

    dot_hits = find_context_snippets(body, MIDDLE_DOTS)
    if dot_hits:
        issues.append(
            "가운데 점 계열 문자 발견: "
            + ", ".join(f"'{c}' (주변: ...{ctx}...)" for c, ctx in dot_hits[:5])
            + ("" if len(dot_hits) <= 5 else f" 외 {len(dot_hits) - 5}건")
        )

    body_without_citations = CITATION_PAREN_RE.sub("", body)
    paren_hits = find_context_snippets(body_without_citations, HALFWIDTH_PARENS + FULLWIDTH_PARENS)
    if paren_hits:
        issues.append(
            "소괄호 사용 발견 (책/작품 제목 뒤 저자 표기 '제목'(저자) 는 예외): "
            + ", ".join(f"'{c}' (주변: ...{ctx}...)" for c, ctx in paren_hits[:5])
            + ("" if len(paren_hits) <= 5 else f" 외 {len(paren_hits) - 5}건")
        )

    for w in BANNED_WORDS:
        if w in body:
            issues.append(f"금지 단어 '{w}' 사용 발견")

    for pat in VAGUE_PRAISE_PATTERNS:
        m = re.search(pat, body)
        if m:
            issues.append(f"막연한 칭찬 표현 발견: '{m.group(0)}' — 구체적 행동/과정으로 대체 필요")

    quote_hits = find_context_snippets(body, CURLY_QUOTES)
    if quote_hits or STRAIGHT_DOUBLE_QUOTE in body:
        issues.append("인용부호가 작은따옴표(') 로 통일되지 않음. 큰따옴표나 스마트 따옴표가 섞여 있음")

    if "\n" in body:
        issues.append("여러 문단으로 나뉘어 있음. 한 문단으로 이어서 작성해야 함")

    if not ends_with_mieum_batchim(body):
        warnings.append(
            "문장이 명사형 종결어미(ㅁ 받침으로 끝나는 형태. 예: 함/음/임/힘)로 끝나지 않는 것으로 보임. "
            "마지막 문장의 서술어를 확인할 것"
        )

    comma_count = body.count(",") + body.count("，")
    if char_count > 0 and comma_count / max(char_count, 1) > 0.012:
        warnings.append(
            f"쉼표가 {comma_count}개로 다소 많은 편임(글자 수 대비). 쉼표가 많은 문장은 AI가 쓴 것처럼 읽히기 쉬우니, "
            "꼭 필요한 경우가 아니면 문장을 끊거나 연결어미로 자연스럽게 이어보는 것을 고려할 것."
        )

    intro_patterns = ["시간에 진행한", "수업에서 진행한", "수업 시간에", "시간에 실시한"]
    head = body[:40]
    for p in intro_patterns:
        if p in head:
            warnings.append(
                f"문장 초반에 '{p}' 같은 교과/수업 소개 문구가 있음. 세특은 이미 해당 교과 아래 기록되므로 "
                "교과명이나 수업명을 다시 소개할 필요 없이 활동 내용으로 바로 들어가는 것이 자연스러움."
            )
            break

    return {
        "char_count": char_count,
        "target_chars": target_chars,
        "had_count_annotation": had_count_annotation,
        "issues": issues,
        "warnings": warnings,
        "passed": len(issues) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="세특 초안 규정 준수 점검")
    parser.add_argument("text", nargs="?", help="점검할 세특 텍스트 (직접 입력)")
    parser.add_argument("--file", help="점검할 텍스트가 담긴 파일 경로")
    parser.add_argument("--target", type=int, default=500, help="목표 글자 수 (기본 500)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("점검할 텍스트가 비어 있음.")
        sys.exit(1)

    result = check(text, target_chars=args.target)

    note = " (파일 끝 글자 수 표기는 제외하고 계산함)" if result["had_count_annotation"] else ""
    print(f"글자 수: {result['char_count']}자 (목표 {result['target_chars']}자){note}")
    print()

    if result["issues"]:
        print(f"위반 사항 {len(result['issues'])}건:")
        for i, issue in enumerate(result["issues"], 1):
            print(f"  {i}. {issue}")
    else:
        print("기계적으로 확인 가능한 위반 사항 없음.")

    if result["warnings"]:
        print()
        print("참고 (자동 판단이 어려운 항목, 직접 확인 권장):")
        for w in result["warnings"]:
            print(f"  - {w}")

    print()
    print("PASS" if result["passed"] else "FAIL")
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
