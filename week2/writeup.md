# Week 2 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: **TODO** \
SUNet ID: **TODO** \
Citations: **TODO**

This assignment took me about **TODO** hours to do. 


## YOUR RESPONSES
For each exercise, please include what prompts you used to generate the answer, in addition to the location of the generated response. Make sure to clearly add comments in your code documenting which parts are generated.

### Exercise 1: Scaffold a New Feature
Prompt: 
```
请在week2/app/services/extract.py内，参考extract_action_items()的功能，实现一个LLM驱动的extract_action_items_llm()函数，利用Ollama调用llama3.1:8b模型实现待办事项提取，使用Ollama的Structured outputs（参考：https://ollama.com/blog/structured-outputs），并编写恰当的system prompt。不需要运行测试或修改其他地方。
``` 

Generated Code Snippets:
```
week2/app/services/extract.py:19-37, 88-137
```

### Exercise 2: Add Unit Tests
Prompt: 
```
请在week2/tests/test_extract.py添加extract_action_items_llm()的单元测试，涵盖多种输入形式（例如项目符号列表、带关键词前缀的行、空输入），并运行测试。不需要mock LLM调用。
``` 

Generated Code Snippets:
```
week2/tests/test_extract.py:5, 23-63
```

### Exercise 3: Refactor Existing Code for Clarity
Prompt: 
```
请对 week2 后端做一个小范围清晰度重构。
具体要求：
1. 新增 week2/app/schemas.py 整理 Pydantic schemas，为现有 backend API 提供清晰的请求和响应模型。
2. 修改 week2/app/routers/action_items.py 和 week2/app/routers/notes.py，使用这些 schemas 替代 Dict[str, Any]，保持现有 API 路径和响应结构兼容。
3. 清理数据库层 week2/app/db.py：增加 sqlite3.Row 到稳定 plain dict 的转换 helper（显式指定字段名和类型），并让 list/get 函数尽量返回这些 dict。让 mark_action_item_done() 返回 bool，表示是否真的更新了记录。
4. 修改 mark done endpoint：如果 action_item_id 不存在，返回 404。
5. 修改 week2/app/main.py，把 import 时直接 init_db() 改成 FastAPI lifespan，在 app 启动时初始化数据库。
6. 修改 LLM 模型配置，让 extract.py 中的模型名从环境变量 OLLAMA_MODEL 读取，默认仍为 llama3.1:8b。
7. 不要改变现有功能语义，不要重构前端，保持改动小而清楚。
``` 

Generated/Modified Code Snippets:
```
week2/app/schemas.py:1-57
week2/app/routers/action_items.py:3, 8-13, 19-50
week2/app/routers/notes.py:3, 6-30
week2/app/db.py:6, 14-25, 67-83, 94-109, 126-149
week2/app/main.py:3-5, 15-21
week2/app/services/extract.py:19
```


### Exercise 4: Use Agentic Mode to Automate a Small Task
Prompt: 
```
将extract_action_items_llm()集成为一个新接口。更新前端页面，新增一个 “Extract LLM” 按钮，点击该按钮后即可通过新接口触发提取流程。
新增一个接口，用于获取全部笔记。修改前端页面，添加 “List Notes” 按钮，点击该按钮即可获取并展示所有笔记。
``` 

Generated Code Snippets:
```
week2/app/routers/action_items.py:3, 15, 21-48
week2/app/routers/notes.py:25-27
week2/frontend/index.html:27-28, 36-96
```


### Exercise 5: Generate a README from the Codebase
Prompt: 
```
分析week2现有代码库，生成结构完整的README.md文件。该自述文件至少需包含以下内容： 
项目简要概述
项目环境搭建与运行方法
接口地址及功能说明
测试套件运行指南
``` 

Generated Code Snippets:
```
week2/README.md:1-268
```


## SUBMISSION INSTRUCTIONS
1. Hit a `Command (⌘) + F` (or `Ctrl + F`) to find any remaining `TODO`s in this file. If no results are found, congratulations – you've completed all required fields. 
2. Make sure you have all changes pushed to your remote repository for grading.
3. Submit via Gradescope. 
