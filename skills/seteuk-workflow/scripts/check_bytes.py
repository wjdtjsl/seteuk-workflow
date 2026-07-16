#!/usr/bin/env python3
"""
check_bytes.py

세특 초안이 나이스(NEIS) 기준 목표 바이트 수에 얼마나 가까운지 확인한다.

많은 학교의 나이스 시스템은 세특 글자 수 제한을 바이트 단위로 관리하며, 교사들은
엑셀에서 다음 수식으로 바이트 수를 확인한다 (E3는 세특 텍스트가 든 셀의 예시):

    =(LENB(E3)-LEN(E3))*2+LEN(E3)

이 수식은 영문/숫자/공백/기호 한 글자를 1바이트로, 한글 음절 한 글자를 3바이트로 계산하는
것과 수학적으로 같다. 즉 한글과 영문/숫자/기호로만 이루어진 일반적인 세특 문장이라면, 이
수식의 결과는 그 텍스트를 UTF-8로 인코딩했을 때의 바이트 길이와 정확히 같다. 이 스크립트는
매번 엑셀을 열지 않고도 같은 숫자를 확인할 수 있게 해준다.

주의: 이모지, 한자, 특수 기호처럼 한글 음절이나 ASCII가 아닌 다른 다국어 문자가 섞이면
실제 엑셀 수식 결과와 이 스크립트의 계산이 달라질 수 있다. 세특에는 애초에 그런 문자를
쓰지 않는 것이 규정에도 맞다.

사용법:
    python3 check_bytes.py "세특 문단 전체 텍스트"
    python3 check_bytes.py --file draft.txt
    python3 check_bytes.py --file draft.txt --target 1500 --tolerance 40
"""

import argparse
import sys


def excel_formula_equivalent_bytes(text):
    """(LENB(cell)-LEN(cell))*2+LEN(cell) 수식과 동일한 바이트 수를 반환한다.

    한글 음절과 ASCII 문자로만 이루어진 텍스트에서는 이 값이 UTF-8 인코딩 바이트 길이와
    정확히 일치한다 (한글 음절 1자 = 3바이트, ASCII 1자 = 1바이트).
    """
    return len(text.encode("utf-8"))


def non_ascii_non_hangul_chars(text):
    """이모지, 한자 등 한글 음절도 ASCII도 아닌 문자를 찾아 경고에 활용한다."""
    HANGUL_BASE = 0xAC00
    HANGUL_END = 0xD7A3
    hits = []
    for ch in text:
        code = ord(ch)
        if code < 128:
            continue
        if HANGUL_BASE <= code <= HANGUL_END:
            continue
        if ch in "'‘’":  # 작은따옴표류는 이미 다른 규칙에서 다룸
            continue
        hits.append(ch)
    return hits


def check(text, target_bytes=1500, tolerance=50):
    char_count = len(text.strip())
    byte_count = excel_formula_equivalent_bytes(text.strip())

    low = target_bytes - tolerance
    high = target_bytes + tolerance
    in_range = low <= byte_count <= high

    unusual_chars = sorted(set(non_ascii_non_hangul_chars(text)))

    return {
        "char_count": char_count,
        "byte_count": byte_count,
        "target_bytes": target_bytes,
        "tolerance": tolerance,
        "low": low,
        "high": high,
        "in_range": in_range,
        "unusual_chars": unusual_chars,
    }


def main():
    parser = argparse.ArgumentParser(description="세특 초안 나이스 바이트 수 점검 (엑셀 LENB 수식과 동일한 계산)")
    parser.add_argument("text", nargs="?", help="점검할 세특 텍스트 (직접 입력)")
    parser.add_argument("--file", help="점검할 텍스트가 담긴 파일 경로")
    parser.add_argument("--target", type=int, default=1500, help="목표 바이트 수 (기본 1500)")
    parser.add_argument("--tolerance", type=int, default=50, help="허용 오차, 바이트 단위 (기본 ±50)")
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

    result = check(text, target_bytes=args.target, tolerance=args.tolerance)

    print(f"글자 수: {result['char_count']}자")
    print(
        f"바이트 수(엑셀 =(LENB-LEN)*2+LEN 수식과 동일): {result['byte_count']}바이트 "
        f"(목표 {result['target_bytes']} ±{result['tolerance']}바이트, "
        f"허용 범위 {result['low']}~{result['high']}바이트)"
    )

    if result["unusual_chars"]:
        print(
            "참고: 한글 음절/ASCII가 아닌 문자가 포함되어 있어 실제 엑셀 계산과 달라질 수 있음: "
            + ", ".join(result["unusual_chars"])
        )

    print()
    if result["in_range"]:
        print("PASS - 목표 범위 안에 있음.")
        sys.exit(0)
    else:
        diff = result["byte_count"] - result["target_bytes"]
        direction = "많음 (줄여야 함)" if diff > 0 else "적음 (늘려야 함)"
        print(f"FAIL - 목표보다 {abs(diff)}바이트 {direction}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
