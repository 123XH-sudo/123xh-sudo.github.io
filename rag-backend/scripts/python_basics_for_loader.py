#!/usr/bin/env python3
"""
Python 基础 · 为读懂 loader.py 而学

用法（在 rag-backend 目录）：
    python scripts/python_basics_for_loader.py          # 运行全部演示
    python scripts/python_basics_for_loader.py --lesson 3   # 只运行第 3 课

建议：每课先看打印输出，再改「你的练习」区里的代码自己试。
"""
from __future__ import annotations

import sys


def lesson1_str_and_slice():
    """第 1 课：字符串 str 与切片 —— 对应 text[match.end():]"""
    print("\n" + "=" * 60)
    print("第 1 课：字符串 str 与切片")
    print("=" * 60)

    text = "abcdefgh"
    print("原字符串:", repr(text))
    print("text[0]   第1个字符:", text[0])       # 'a'
    print("text[3:]  从下标3到末尾:", text[3:])   # 'defgh'  ← 类似 text[match.end():]
    print("text[:3]  从头到下标3(不含):", text[:3])

    body = "  \n## 标题\n正文  "
    print("strip 去首尾空白:", repr(body.strip()))

    title = "RAG"
    prefixed = f"【{title} > 章节1】\n"  # f-string 插值
    print("f-string:", prefixed)


def lesson2_dict():
    """第 2 课：字典 dict —— 对应 metadata、meta.get()"""
    print("\n" + "=" * 60)
    print("第 2 课：字典 dict（键值对）")
    print("=" * 60)

    meta = {
        "title": "RAG 系统基础",
        "tags": ["RAG", "LLM"],
        "layout": "single",
    }
    print("type(meta):", type(meta))
    print('meta["title"]:', meta["title"])
    print('meta.get("date", "无日期"):', meta.get("date", "无日期"))  # 没有 date 键不报错

    empty = {}
    print("空 dict:", empty, type(empty))


def lesson3_tuple_and_unpack():
    """第 3 课：tuple 与 return 拆包 —— 对应 return metadata, body"""
    print("\n" + "=" * 60)
    print("第 3 课：tuple 与拆包")
    print("=" * 60)

    # return a, b 实际返回 tuple
    def fake_parse():
        metadata = {"title": "测试"}
        body = "## 正文"
        return metadata, body  # 等价 return (metadata, body)

    result = fake_parse()
    print("返回值 type:", type(result), "长度:", len(result))

    meta, body = fake_parse()  # 拆包
    print("meta type:", type(meta), "→", meta)
    print("body type:", type(body), "→", body)


def lesson4_none_and_or():
    """第 4 课：None、if not、or —— 对应 if not match、... or {}"""
    print("\n" + "=" * 60)
    print("第 4 课：None、if not、or")
    print("=" * 60)

    match = None  # 模拟 re.match 失败
    if not match:
        print("match 是 None → if not match 成立")

    match_ok = "假装是 Match 对象"
    if not match_ok:
        print("不会打印")
    else:
        print("match 有值 → 继续解析")

    # or：左边是「空/None」就用右边
    print(None or {})           # {}
    print("hello" or "默认")    # hello
    print(None or [])           # []


def lesson5_list():
    """第 5 课：list 与列表推导 —— 对应 post_tags=[str(t) for t in tags]"""
    print("\n" + "=" * 60)
    print("第 5 课：list 与列表推导")
    print("=" * 60)

    tags = ["RAG", "LLM"]
    post_tags = [str(t) for t in tags]
    print("列表推导结果:", post_tags)

    # 等价写法
    post_tags2 = []
    for t in tags:
        post_tags2.append(str(t))
    print("for 循环等价:", post_tags2)


def lesson6_function():
    """第 6 课：函数 def —— 整体结构"""
    print("\n" + "=" * 60)
    print("第 6 课：函数")
    print("=" * 60)

    def add(a: int, b: int) -> int:
        return a + b

    print("add(2,3) =", add(2, 3))
    print("类型注解 a: int 是给人类/IDE看的，运行时不强制检查")


def lesson7_loader_simulation():
    """第 7 课：不用正则，模拟 parse_front_matter 逻辑"""
    print("\n" + "=" * 60)
    print("第 7 课：模拟 loader（简化版，无 regex）")
    print("=" * 60)

    raw = "---\ntitle: 我的博客\n---\n## 第一节\n内容在这里"

    if not raw.startswith("---"):
        meta, body = {}, raw
    else:
        parts = raw.split("---", 2)  # 最多分 3 段（教学用，真实代码用 regex）
        yaml_text = parts[1].strip()
        body = parts[2].strip() if len(parts) > 2 else ""
        meta = {}
        for line in yaml_text.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    print("meta (dict):", meta)
    print("body (str):", repr(body))
    print("\n→ 真实 loader 用 regex + yaml.safe_load，但返回同样是 (dict, str)")


LESSONS = {
    1: lesson1_str_and_slice,
    2: lesson2_dict,
    3: lesson3_tuple_and_unpack,
    4: lesson4_none_and_or,
    5: lesson5_list,
    6: lesson6_function,
    7: lesson7_loader_simulation,
}


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--lesson":
        n = int(sys.argv[2])
        LESSONS[n]()
        return

    print("Python 基础 · 共 7 课（为 loader.py 服务）")
    for fn in LESSONS.values():
        fn()
    print("\n" + "=" * 60)
    print("全部演示完毕。建议：")
    print("  python scripts/python_basics_for_loader.py --lesson 1")
    print("  一课一课看，每课改脚本里的变量自己试。")
    print("=" * 60)


if __name__ == "__main__":
    main()
