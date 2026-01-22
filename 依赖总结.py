from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class RequirementsResult:
	packages: tuple[str, ...]
	requirements_txt: str


def generate_requirements_txt(
	project_root: Optional[str | os.PathLike[str]] = None,
	*,
	scan_dirs: Iterable[str] = ("codes",),
	output_path: Optional[str | os.PathLike[str]] = None,
) -> RequirementsResult:
	"""遍历项目 Python 代码文件，基于 import 静态分析生成 requirements.txt 内容。

	目标：输出“可直接 pip 安装”的三方依赖列表（排除标准库 & 项目内模块）。

	参数
	- project_root: 项目根目录（默认取本文件所在目录）
	- scan_dirs: 要扫描的子目录（默认 codes/）
	- output_path: 如果提供，则把 requirements_txt 写入该路径

	返回
	- RequirementsResult(packages, requirements_txt)
	"""

	root = Path(project_root) if project_root else Path(__file__).resolve().parent
	root = root.resolve()

	# 1) 收集项目内“顶层模块名”，用来排除本地 import
	local_top_level: set[str] = set()
	for scan_dir in scan_dirs:
		base = (root / scan_dir).resolve()
		if not base.exists():
			continue
		for path in base.rglob("*.py"):
			if any(part in {"__pycache__", ".venv", "venv", "env", "build", "dist"} for part in path.parts):
				continue
			local_top_level.add(path.stem)

			# 识别包目录（包含 __init__.py）
			try:
				rel = path.relative_to(base)
			except Exception:
				continue
			if len(rel.parts) >= 2 and rel.parts[-1] == "__init__.py":
				local_top_level.add(rel.parts[0])

	# 2) 标准库模块集合（Python 3.10+ 有 sys.stdlib_module_names）
	try:
		import sys

		stdlib = set(getattr(sys, "stdlib_module_names", set()))
	except Exception:
		stdlib = set()

	# 3) 解析所有 import
	imported_top_level: set[str] = set()
	token_hits: set[str] = set()  # 用于检测隐式依赖（例如 PDF 解析库）

	def _record_module(mod: str) -> None:
		top = (mod or "").split(".", 1)[0].strip()
		if top:
			imported_top_level.add(top)

	for scan_dir in scan_dirs:
		base = (root / scan_dir).resolve()
		if not base.exists():
			continue
		for path in base.rglob("*.py"):
			if any(part in {"__pycache__", ".venv", "venv", "env", "build", "dist"} for part in path.parts):
				continue

			try:
				source = path.read_text(encoding="utf-8")
			except UnicodeDecodeError:
				source = path.read_text(encoding="gbk", errors="ignore")

			# 记录关键 token，补充一些运行时依赖
			if "PyPDFLoader" in source:
				token_hits.add("PyPDFLoader")
			if "WebBaseLoader" in source:
				token_hits.add("WebBaseLoader")
			if "Tongyi" in source:
				token_hits.add("Tongyi")
			if "Tavily" in source:
				token_hits.add("Tavily")

			try:
				tree = ast.parse(source, filename=str(path))
			except SyntaxError:
				# 某些临时文件/不完整文件不阻断整体生成
				continue

			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					for alias in node.names:
						_record_module(alias.name)
				elif isinstance(node, ast.ImportFrom):
					if node.level and node.level > 0:
						# 相对导入：视为项目内
						continue
					if node.module:
						_record_module(node.module)

	# 4) 过滤：标准库 + 本地模块
	third_party = {
		m
		for m in imported_top_level
		if m
		and m not in stdlib
		and m not in local_top_level
		and m not in {"__future__", "typing", "dataclasses"}
	}

	# 5) 模块名 -> pip 包名映射
	module_to_pip = {
		# LangChain 拆分后的包名
		"langchain": "langchain",
		"langchain_core": "langchain-core",
		"langchain_community": "langchain-community",
		"langchain_openai": "langchain-openai",
		"langchain_text_splitters": "langchain-text-splitters",
		"langchain_tavily": "langchain-tavily",

		# 常见三方
		"yaml": "PyYAML",
		"requests": "requests",
		"bs4": "beautifulsoup4",
		"dateutil": "python-dateutil",

		# 兼容运行路径里可能出现的依赖
		"openai": "openai",
		"tavily": "tavily-python",
		"dashscope": "dashscope",
	}

	packages: set[str] = set()
	for mod in sorted(third_party):
		packages.add(module_to_pip.get(mod, mod))

	# 6) 补充一些“代码里用了但未必显式 import”的依赖
	# - PyPDFLoader 通常需要 pypdf
	if "PyPDFLoader" in token_hits:
		packages.add("pypdf")
	# - TavilySearchResults 在某些环境需要 tavily-python
	if "Tavily" in token_hits:
		packages.add("tavily-python")
	# - Tongyi 依赖 dashscope
	if "Tongyi" in token_hits:
		packages.add("dashscope")

	requirements_lines = [p for p in sorted(packages) if p]
	requirements_txt = "\n".join(requirements_lines) + ("\n" if requirements_lines else "")

	if output_path is not None:
		out = Path(output_path)
		if not out.is_absolute():
			out = (root / out).resolve()
		out.parent.mkdir(parents=True, exist_ok=True)
		out.write_text(requirements_txt, encoding="utf-8")

	return RequirementsResult(packages=tuple(requirements_lines), requirements_txt=requirements_txt)


if __name__ == "__main__":
	# 默认在项目根目录生成 requirements.generated.txt
	result = generate_requirements_txt(output_path="requirements.generated.txt")
	print("生成依赖数量:", len(result.packages))
	print("输出文件:", str((Path(__file__).resolve().parent / "requirements.generated.txt").resolve()))
