import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import App from "./App.vue";
import { createUniPolyfill } from "./utils/uni-polyfill";

// ===== Route definitions =====
const routes = [
  { path: "/", redirect: "/pages/index/index" },
  {
    path: "/pages/index/index",
    name: "home",
    component: () => import("./pages/index/index.vue"),
    meta: { title: "思政情景工坊", tab: 0, layout: "dashboard" },
  },
  {
    path: "/pages/login/login",
    name: "login",
    component: () => import("./pages/login/login.vue"),
    meta: { title: "登录", hideNav: true, hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/interview/interview",
    name: "interview",
    component: () => import("./pages/interview/interview.vue"),
    meta: { title: "入党谈话", tab: 1, layout: "dashboard" },
  },
  {
    path: "/pages/interview/practice",
    name: "practice",
    component: () => import("./pages/interview/practice.vue"),
    meta: { title: "谈话练习", hideTab: true, layout: "workspace" },
  },
  {
    path: "/pages/interview/report",
    name: "report",
    component: () => import("./pages/interview/report.vue"),
    meta: { title: "评估报告", hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/history/history",
    name: "history",
    component: () => import("./pages/history/history.vue"),
    meta: {
      title: "党史现场纪事",
      hideNav: true,
      hideTab: true,
      immersive: true,
    },
  },
  {
    path: "/pages/history/scenario",
    name: "scenario",
    component: () => import("./pages/history/scenario.vue"),
    meta: {
      title: "沉浸式党史书卷",
      hideNav: true,
      hideTab: true,
      immersive: true,
    },
  },
  {
    path: "/pages/knowledge/knowledge",
    name: "knowledge",
    component: () => import("./pages/knowledge/knowledge.vue"),
    meta: { title: "知识库", tab: 3, layout: "dashboard" },
  },
  {
    path: "/pages/knowledge/document",
    name: "doc",
    component: () => import("./pages/knowledge/document.vue"),
    meta: { title: "文档详情", hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/knowledge/template",
    name: "template",
    component: () => import("./pages/knowledge/template.vue"),
    meta: { title: "模板生成", hideTab: true, layout: "workspace" },
  },
  {
    path: "/pages/knowledge/ask",
    name: "knowledge-ask",
    component: () => import("./pages/knowledge/ask.vue"),
    meta: { title: "知识问答", hideTab: true, layout: "workspace", lockViewport: true },
  },
  {
    path: "/pages/knowledge/favorites",
    name: "knowledge-favorites",
    component: () => import("./pages/knowledge/favorites.vue"),
    meta: { title: "我的资料夹", hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/knowledge/manage",
    name: "knowledge-manage",
    component: () => import("./pages/knowledge/manage.vue"),
    meta: { title: "资料管理", hideTab: true, layout: "workspace" },
  },
  {
    path: "/pages/community/community",
    name: "community",
    component: () => import("./pages/community/community.vue"),
    meta: { title: "成长社区", tab: 2, layout: "dashboard" },
  },
  {
    path: "/pages/community/post-detail",
    name: "post",
    component: () => import("./pages/community/post-detail.vue"),
    meta: { title: "帖子详情", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/create-post",
    name: "create-post",
    component: () => import("./pages/community/create-post.vue"),
    meta: { title: "发布帖子", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/task-detail",
    name: "community-task",
    component: () => import("./pages/community/task-detail.vue"),
    meta: { title: "教师任务", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/task-manage",
    name: "community-task-manage",
    component: () => import("./pages/community/task-manage.vue"),
    meta: { title: "教师工作台", hideTab: true, layout: "workspace" },
  },
  {
    path: "/pages/community/notifications",
    name: "community-notifications",
    component: () => import("./pages/community/notifications.vue"),
    meta: { title: "社区消息", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/my-community",
    name: "my-community",
    component: () => import("./pages/community/my-community.vue"),
    meta: { title: "我的社区", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/moderation",
    name: "community-moderation",
    component: () => import("./pages/community/moderation.vue"),
    meta: { title: "内容审核", hideTab: true, layout: "workspace" },
  },
  {
    path: "/pages/community/growth",
    name: "growth",
    component: () => import("./pages/community/growth.vue"),
    meta: { title: "成长档案", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/practices",
    name: "my-practices",
    component: () => import("./pages/community/practices.vue"),
    meta: { title: "训练中心", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/community/profile",
    name: "profile",
    component: () => import("./pages/community/profile.vue"),
    meta: { title: "我的", tab: 4, layout: "dashboard" },
  },
  {
    path: "/pages/debate/debate",
    name: "debate",
    component: () => import("./pages/debate/debate.vue"),
    meta: { title: "辩论赛陪练", hideTab: true, layout: "dashboard" },
  },
  {
    path: "/pages/debate/arena",
    name: "arena",
    component: () => import("./pages/debate/arena.vue"),
    meta: { title: "辩论赛场", hideTab: true, layout: "workspace", lockViewport: true },
  },
  {
    path: "/pages/debate/feedback",
    name: "debate-feedback",
    component: () => import("./pages/debate/feedback.vue"),
    meta: { title: "辩论评估", hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/tour/tour",
    name: "tour",
    component: () => import("./pages/tour/tour.vue"),
    meta: {
      title: "红色山河研学图志",
      hideNav: true,
      hideTab: true,
      immersive: true,
    },
  },
  {
    path: "/pages/tour/site",
    name: "site",
    component: () => import("./pages/tour/site.vue"),
    meta: {
      title: "沉浸式研学图志",
      hideNav: true,
      hideTab: true,
      immersive: true,
    },
  },
  {
    path: "/pages/tour/report",
    name: "tour-report",
    component: () => import("./pages/tour/report.vue"),
    meta: { title: "研学报告", hideTab: true, layout: "reading" },
  },
  {
    path: "/pages/community/reports",
    name: "my-reports",
    component: () => import("./pages/community/reports.vue"),
    meta: { title: "我的报告", hideTab: true, layout: "dashboard" },
  },
  // Fallback: unknown paths redirect to the home tab instead of a blank screen.
  { path: "/:pathMatch(.*)*", redirect: "/pages/index/index" },
];

const router = createRouter({ history: createWebHashHistory(), routes });
(window as any).__router__ = router;

router.beforeEach((to) => {
  const publicPaths = ["/pages/login/login"];
  const token = localStorage.getItem("token");
  if (!token && !publicPaths.includes(to.path)) return "/pages/login/login";
  if (token && to.path === "/pages/login/login") return "/pages/index/index";
  return true;
});

// ===== Create app =====
const app = createApp(App);
app.use(createPinia());
app.use(router);
createUniPolyfill(router);

// ===== Mount (no component registrations - all tags are native HTML) =====
app.mount("#app");
