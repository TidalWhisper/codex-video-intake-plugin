# 任务：Provider 接入后的硬化测试

目标：保证真实 provider 接入后，低能力模型也不能虚报进度。

必须测试：

1. API key 缺失时，OpenAI provider 必须失败并写 errors。
2. ComfyUI 不在线时，ComfyUI provider 必须失败并写 errors。
3. workflow 文件缺失时，不能继续执行。
4. workflow node mapping 缺失时，不能继续执行。
5. output_path 不存在时，final validator 必须失败。
6. output_path 文件大小为 0 时，final validator 必须失败。
7. 一部分 job 成功、一部分失败时，manifest 必须准确记录 partial_failed。

完成后运行：

```cmd
run_all_tests.cmd
```
