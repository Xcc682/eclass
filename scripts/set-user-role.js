#!/usr/bin/env node

/**
 * Change one user's application role in the Docker PostgreSQL database.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... node set-user-role.js <phone> <role>
 *
 * Roles: student, teacher, admin
 */

const { Client } = require('pg')

const ALLOWED_ROLES = new Set(['student', 'teacher', 'admin'])

function usage(message) {
  if (message) console.error(`Error: ${message}\n`)
  console.error('Usage: node set-user-role.js <phone> <student|teacher|admin>')
  process.exit(2)
}

async function main() {
  const [, , phone, role] = process.argv
  if (!phone || !role) usage('手机号和角色均为必填项。')
  if (!ALLOWED_ROLES.has(role)) usage(`不支持的角色：${role}`)
  if (!process.env.DATABASE_URL) usage('未设置 DATABASE_URL。')

  const client = new Client({ connectionString: process.env.DATABASE_URL })
  await client.connect()

  try {
    await client.query('BEGIN')
    const before = await client.query(
      'SELECT id, phone, nickname, role FROM users WHERE phone = $1 FOR UPDATE',
      [phone]
    )

    if (before.rowCount !== 1) {
      await client.query('ROLLBACK')
      console.error(`未找到手机号为 ${phone} 的用户；请让该用户先登录一次。`)
      process.exitCode = 1
      return
    }

    const result = await client.query(
      `UPDATE users
       SET role = $1, updated_at = CURRENT_TIMESTAMP
       WHERE phone = $2
       RETURNING id, phone, nickname, role, updated_at`,
      [role, phone]
    )
    await client.query('COMMIT')
    console.log('角色更新成功：')
    console.table(result.rows)
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {})
    throw error
  } finally {
    await client.end()
  }
}

main().catch((error) => {
  console.error('角色更新失败：', error.message)
  process.exit(1)
})
