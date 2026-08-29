"""
LangGraph 最小示例：三节点 StateGraph

核心概念（阶段 1 必掌握）：
- State：图在节点之间传递的「共享数据结构」，类似全局变量但类型安全
- Node：一个 Python 函数，接收 State，返回 State 的**部分更新**（dict）
- Edge：节点之间的连接；START / END 是 LangGraph 内置的特殊节点

对比 LangChain Chain：
- Chain 是 A→B→C 线性管道，难以插入条件分支
- LangGraph 用「图」描述流程，后续可加「检索置信度低 → 走降级分支」
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class HelloState(TypedDict):
    """图的状态：每个字段都会在节点间传递。"""

    user_input: str
    processed: str
    final_answer: str


def receive_input(state: HelloState) -> dict:
    """节点 1：接收用户输入，做最简预处理。"""
    text = state["user_input"].strip()
    return {"processed": f"[received] {text}"}


def transform(state: HelloState) -> dict:
    """节点 2：模拟中间处理（阶段 4 这里会变成 retrieve + rerank）。"""
    return {"processed": state["processed"].upper()}


def generate_output(state: HelloState) -> dict:
    """节点 3：生成最终输出（阶段 4 这里会调用 LLM）。"""
    return {"final_answer": f"Hello RAG! 处理结果: {state['processed']}"}


def build_hello_graph():
    """
    构建并编译 StateGraph。

    compile() 返回的可调用对象支持 .invoke(initial_state)。
    """
    graph = StateGraph(HelloState)

    graph.add_node("receive_input", receive_input)
    graph.add_node("transform", transform)
    graph.add_node("generate_output", generate_output)

    graph.add_edge(START, "receive_input")
    graph.add_edge("receive_input", "transform")
    graph.add_edge("transform", "generate_output")
    graph.add_edge("generate_output", END)

    return graph.compile()


def run_hello_graph(user_input: str) -> HelloState:
    """便捷入口：传入字符串，返回完整 State。"""
    app = build_hello_graph()
    return app.invoke({"user_input": user_input, "processed": "", "final_answer": ""})
