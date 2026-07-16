#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
byte_counter.py

나이스(NEIS) 기준으로 세특 텍스트의 바이트 수를 계산한다.
한글 완성형 문자는 3바이트, 그 외(영문, 숫자, 공백, 특수문자, 줄바꿈)는 1바이트로 계산한다.

사용법:
    python3 byte_counter.py "여기에 세특 텍스트"
    python3 byte_counter.py --file 경로.txt
    python3 byte_counter.py --file 경로.txt --limit 1500
    echo "텍스트" | python3 byte_counter.py --stdin
"""

import argparse
import sys


def count_neis_bytes(text: str) -> int:
    total = 0
    for ch in text:
        if "가" <= ch <= "힣":
            total += 3
        else:
            total += 1
    return total


def main():
    parser = argparse.ArgumentParser(description="NEIS 기준 세특 바이트 수 계산")
    parser.add_argument("text", nargs="?", default=None, help="계산할 텍스트")
    parser.add_argument("--file", default=None, help="텍스트 파일 경로")
    parser.add_argument("--stdin", action="store_true", help="표준입력에서 텍스트 읽기")
    parser.add_argument("--limit", type=int, default=1500, help="비교할 제한치 (기본 1500Byte)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.stdin:
        text = sys.stdin.read()
    elif args.text is not None:
        text = args.text
    else:
        parser.error("텍스트, --file, --stdin 중 하나는 지정해야 합니다.")
        return

    byte_count = count_neis_bytes(text)
    char_count = len(text)
    status = "초과" if byte_count > args.limit else "이내"
    remaining = args.limit - byte_count

    print("글자 수: {}자".format(char_count))
    print("바이트 수: {}Byte".format(byte_count))
    print("제한: {}Byte ({})".format(args.limit, status))
    if status == "초과":
        print("초과분: {}Byte".format(-remaining))
    else:
        print("여유분: {}Byte".format(remaining))
    print("주의: 학년도/영역별 최신 제한치는 나이스 공지로 재확인하세요.")


if __name__ == "__main__":
    main()
