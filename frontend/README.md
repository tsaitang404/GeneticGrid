# GeneticGrid Frontend

基于 Vue 3 + Vite + Lightweight Charts 的交易平台前端

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── components/          # Vue 组件
│   │   ├── chart/          # 图表相关组件
│   │   ├── indicators/     # 指标选择器
│   │   └── tools/          # 画线工具
│   ├── composables/        # 组合式函数
│   ├── stores/             # Pinia 状态管理
│   ├── utils/              # 工具函数
│   ├── workers/            # Web Workers
│   ├── App.vue             # 根组件
│   └── main.js             # 入口文件
├── public/                 # 静态资源
├── package.json
└── vite.config.js
```
