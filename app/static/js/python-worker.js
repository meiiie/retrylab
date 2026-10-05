import { loadPyodide } from "../vendor/pyodide/pyodide.mjs";

const send = self.postMessage.bind(self);
let python;
try {
  python = await loadPyodide({
    indexURL: new URL("../vendor/pyodide/", import.meta.url).href,
  });
  const response = await fetch(new URL("../python/grader.py", import.meta.url));
  if (!response.ok) throw new Error("Không tải được bộ kiểm tra bài làm.");
  await python.runPythonAsync(await response.text());
  send({
    type: "ready",
    version: python.runPython("__import__('sys').version.split()[0]"),
  });
} catch (exception) {
  send({ type: "init-error", error: exception.message });
}

self.onmessage = async ({ data }) => {
  if (!python || data.type !== "run") return;
  const { id, source, functionName, tests } = data;
  try {
    python.globals.set("_source", source);
    python.globals.set("_name", functionName);
    python.globals.set("_cases_json", JSON.stringify(tests));
    const result = await python.runPythonAsync(
      "json.dumps(grade_submission(_source, _name, json.loads(_cases_json)), ensure_ascii=False)",
    );
    send({ type: "result", id, result: JSON.parse(result) });
  } catch (exception) {
    send({
      type: "result",
      id,
      result: {
        status: "error",
        error: exception.message,
        passed: 0,
        total: tests.length,
        tests: [],
      },
    });
  }
};
