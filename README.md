
#  Code Converter & Compiler

A powerful Gradio-based web app to **convert code** between **Python, C++, Java, and JavaScript**, with **compile/run support** for Python and C++. It uses **Together AI’s LLM** to handle code translation while maintaining functionality and best practices.


---

## 🚀 Features

- ✅ **Language Detection** (Python, C++, Java, JavaScript)
- 🔁 **Convert code** between any of the supported languages
- 🧠 **LLM-powered conversion** via Together API
- 🛠️ **Compile & Run** support for:
  - Python
  - C++ (via `g++`)
- 💻 **Gradio Interface** – Easy to use, clean, and interactive
- 🔐 API Key-based secure integration

---

## 🧠 Supported Conversions

| From → To       | Python | C++ | Java | JavaScript |
|----------------|--------|-----|------|-------------|
| **Python**     | ✅     | ✅  | ✅   | ✅          |
| **C++**        | ✅     | ✅  | ✅   | ✅          |
| **Java**       | ✅     | ✅  | ✅   | ✅          |
| **JavaScript** | ✅     | ✅  | ✅   | ✅          |

> ⚠️ Compile/Run support currently available only for **Python** and **C++**.

---


## 🧪 Run Locally

```bash
python app.py
```

Or inside a Jupyter Notebook:

```python
interface = create_jupyter_interface()
interface.launch(inline=True)
```

---

## 🧰 Tech Stack

- 🧠 LLM: [Together AI](https://platform.together.xyz/)
- 🧪 Interface: [Gradio](https://gradio.app)
- 🔤 Language Detection: Heuristics + Regex
- 🧵 Backend: Python (with `subprocess` for compile/run)


## 🔮 Future Features

- ✅ Add Java and JavaScript compile/run via Docker sandbox
- 🌐 Deploy to Hugging Face Spaces
- 🔄 Language auto-suggestion with confidence
- 📈 Add metrics like conversion time & token usage

---

## 🧑‍💻 Author

**Pradeep Singh Sengar**  
🔗 [Portfolio](https://pradeepsengarr.github.io/i_portfolio/)  
💼 [LinkedIn](https://www.linkedin.com/in/pradeepsengarr)
