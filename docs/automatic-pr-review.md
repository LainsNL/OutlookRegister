# 自动 PR 审核落地说明

## 这次仓库内已经落地了什么

本仓库现在新增了一个最小可用的 GitHub Actions 工作流：

- 文件：`.github/workflows/pr-check.yml`
- 触发条件：
  - 向 `main` 发起 Pull Request
  - 手动 `workflow_dispatch`

当前它会做两类检查：

1. **语法编译检查**
   - 运行：
     ```bash
     python -m py_compile OutlookRegister.py OutlookRegister_patchright.py get_token.py
     ```
2. **配置文件结构烟雾测试**
   - 验证 `config.json` 中关键字段仍然存在
   - 防止 PR 把运行所需的基础配置键误删

这套检查的目标很明确：**先拦住最容易在 PR 阶段再次引入的基础语法错误和配置破坏。**

> 当前这张“自动 PR 检查”PR 是从 `main` 独立开的。由于 `main` 还未合入跨平台修复，  
> 所以这里没有把“非 Windows 直接 `import get_token`”当成现阶段门禁，避免第二张 PR 反过来被第一张 PR 的旧问题卡死。  
> 等跨平台修复 PR 合入后，可以把 workflow 再增强为：
>
> - `import get_token` 跨平台导入烟雾测试
> - localhost OAuth callback helper 检查

---

## 这不等于“自动拦截合并”

只提交 workflow 还不够。

GitHub Actions 负责“跑检查”，但**真正禁止带病合并**，还要在仓库设置里打开以下能力：

1. **Branch protection** 或 **Rulesets**
2. 把 `PR 检查 / Python 基础校验` 设为 **required status check**

也就是说，正确闭环是：

```text
Pull Request -> Actions 自动跑检查 -> Branch Protection 要求检查通过 -> 才允许合并
```

如果不打开 required status checks，这个 workflow 只能提示红绿灯，**不能强制挡住 merge**。

---

## 私有仓库怎么做

这套方案同样适用于私有仓库。

仓库内可提交的部分仍然是：

- `.github/workflows/*.yml`

仓库设置侧需要额外确认：

- 仓库是否允许 GitHub Actions 运行
- 组织/企业策略是否限制第三方 Action
- 是否已在 Branch protection / Rulesets 中启用 required checks

所以“私有仓库自动 PR 审核”本质上分成两层：

### 第一层：仓库内代码配置
- GitHub Actions workflow

### 第二层：仓库/组织设置
- Branch protection / Rulesets
- 必要时配合 CODEOWNERS / required reviewers

---

## 如果要再往上走一步

如果公司已经开通 **GitHub Copilot Business / Enterprise**，可以再考虑打开 **Copilot automatic code review**。

但这部分不是单靠仓库里 commit 一个文件就能完整启用的，它依赖：

- 仓库设置
- 组织策略
- Copilot 授权范围

所以要分清楚：

### 仓库内可落地
- Actions 自动检查
- CODEOWNERS
- PR 模板

### 仓库外设置项
- Branch protection / Rulesets
- Copilot automatic review
- 审批策略

---

## 推荐的最短实施顺序

1. 先合入当前这个 workflow
2. 到 GitHub 仓库设置里把 `PR 检查 / Python 基础校验` 设为 required
3. 再按团队需要决定是否启用：
   - CODEOWNERS
   - PR template
   - Copilot automatic review

---

## 当前方案的边界

当前 workflow **没有**做这些事情：

- 不跑真实 Outlook 注册链路
- 不跑浏览器自动化
- 不验证代理池质量
- 不测试微软 OAuth 真实授权成功率
- 不做当前 `main` 还未具备条件的非 Windows import gate

原因很直接：

- 这些检查不稳定、强依赖外部环境
- 不适合作为 PR 阶段的稳定门禁

PR 门禁应该优先放：

- 稳定
- 可重复
- 与代码回归直接相关

而不是把外部平台风控、代理质量、验证码成功率混进 CI。
