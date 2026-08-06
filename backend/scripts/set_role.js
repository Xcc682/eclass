#!/usr/bin/env node

/**
 * Change a local SQLite user's role by phone number.
 *
 * Usage:
 *   node backend/scripts/set_role.js <phone> <student|teacher|admin>
 *   node backend/scripts/set_role.js <phone> <role> --dry-run
 *   node backend/scripts/set_role.js <phone> <role> --db F:\path\to\dev.db
 */

const fs = require('node:fs')
const path = require('node:path')
const { DatabaseSync } = require('node:sqlite')

const ALLOWED_ROLES = new Set(['student', 'teacher', 'admin'])
const DEFAULT_DATABASE = path.resolve(__dirname, '..', 'dev.db')

function printHelp() {
  console.log(`
更改账户权限（本机 SQLite）

用法：
  node backend/scripts/set_role.js <手机号> <student|teacher|admin> [选项]

角色：
  student   普通学生
  teacher   教师
  admin     管理员

选项：
  --dry-run       只查看将要发生的修改，不写入数据库
  --db <路径>     指定 SQLite 数据库，默认 backend/dev.db
  -h, --help      显示帮助

示例：
  node backend/scripts/set_role.js 13800138000 teacher
  node backend/scripts/set_role.js 13800138000 admin --dry-run
`)
}

function fail(message) {
  console.error(`错误：${message}`)
  process.exitCode = 1
}

function parseArgs(argv) {
  if (argv.includes('-h') || argv.includes('--help')) return { help: true }

  const positional = []
  let databasePath = DEFAULT_DATABASE
  let dryRun = false

  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index]
    if (value === '--dry-run') {
      dryRun = true
    } else if (value === '--db') {
      const next = argv[index + 1]
      if (!next) throw new Error('--db 后必须提供数据库路径')
      databasePath = path.resolve(next)
      index += 1
    } else if (value.startsWith('-')) {
      throw new Error(`未知选项：${value}`)
    } else {
      positional.push(value)
    }
  }

  if (positional.length !== 2) {
    throw new Error('请提供手机号和目标角色；使用 --help 查看示例')
  }

  return {
    help: false,
    phone: positional[0],
    role: positional[1].toLowerCase(),
    databasePath,
    dryRun,
  }
}

function main() {
  let args
  try {
    args = parseArgs(process.argv.slice(2))
  } catch (error) {
    fail(error.message)
    return
  }

  if (args.help) {
    printHelp()
    return
  }
  if (!/^1\d{10}$/.test(args.phone)) {
    fail('手机号格式不正确，应为 11 位中国大陆手机号')
    return
  }
  if (!ALLOWED_ROLES.has(args.role)) {
    fail(`角色只能是 student、teacher 或 admin，当前输入：${args.role}`)
    return
  }
  if (!fs.existsSync(args.databasePath)) {
    fail(`数据库不存在：${args.databasePath}`)
    return
  }

  const database = new DatabaseSync(args.databasePath, { readOnly: args.dryRun })
  try {
    const user = database.prepare(
      'SELECT id, phone, nickname, role, is_active FROM users WHERE phone = ?',
    ).get(args.phone)

    if (!user) {
      fail('账户不存在，请先在网站注册该账号')
      return
    }

    console.log(`账户：${user.nickname || '未设置昵称'}（${user.phone}）`)
    console.log(`当前权限：${user.role}`)
    console.log(`目标权限：${args.role}`)

    if (user.role === args.role) {
      console.log('无需修改：账户已经是目标权限。')
      return
    }
    if (args.dryRun) {
      console.log('预览完成：--dry-run 模式未写入数据库。')
      return
    }

    database.exec('BEGIN IMMEDIATE')
    try {
      const result = database.prepare(
        'UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND role = ?',
      ).run(args.role, user.id, user.role)
      if (result.changes !== 1) {
        throw new Error('账户权限已被其他操作修改，请重新执行脚本')
      }
      database.exec('COMMIT')
    } catch (error) {
      database.exec('ROLLBACK')
      throw error
    }

    const verified = database.prepare('SELECT role FROM users WHERE id = ?').get(user.id)
    if (!verified || verified.role !== args.role) {
      throw new Error('写入后的权限校验失败')
    }
    console.log(`修改成功：${user.role} → ${verified.role}`)
    console.log('提示：如果该账号当前已登录，请退出后重新登录以刷新界面状态。')
  } catch (error) {
    fail(error.message)
  } finally {
    database.close()
  }
}

main()
