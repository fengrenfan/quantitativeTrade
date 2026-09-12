import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchSymbols } from '../api/client'
import type { SymbolHit } from '../api/client'

const TYPE_LABEL: Record<string, string> = { stock: '股', etf: 'ETF', index: '指数' }

interface Props {
  value: string
  name?: string
  onChange: (code: string, name?: string) => void
}

/** 可搜索的标的输入框：支持代码 / 名称 / 拼音首字母，带下拉联想 + 键盘导航。 */
export default function SymbolPicker({ value, name, onChange }: Props) {
  const [text, setText] = useState(value)
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<SymbolHit[]>([])
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(0)
  const boxRef = useRef<HTMLDivElement>(null)
  const seqRef = useRef(0)

  // 外部 value 变化（如首次加载）时同步到输入框
  useEffect(() => {
    setText(value)
  }, [value])

  // 防抖搜索
  useEffect(() => {
    if (text.trim() === '') {
      // 空输入：展示默认常用标的，方便第一次点选
      const seq = ++seqRef.current
      setLoading(true)
      fetchSymbols('', undefined, 20)
        .then((r) => {
          if (seq === seqRef.current) setResults(r.results)
        })
        .catch(() => setResults([]))
        .finally(() => {
          if (seq === seqRef.current) setLoading(false)
        })
      return
    }
    const seq = ++seqRef.current
    const t = setTimeout(() => {
      setLoading(true)
      fetchSymbols(text, undefined, 30)
        .then((r) => {
          if (seq === seqRef.current) {
            setResults(r.results)
            setActive(0)
          }
        })
        .catch(() => {
          if (seq === seqRef.current) setResults([])
        })
        .finally(() => {
          if (seq === seqRef.current) setLoading(false)
        })
    }, 250)
    return () => clearTimeout(t)
  }, [text])

  // 点击外部关闭
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const display = useMemo(() => (name && !open ? `${name} · ${value}` : value), [name, value, open])

  const pick = (hit: SymbolHit) => {
    onChange(hit.code, hit.name)
    setText(hit.code)
    setOpen(false)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => (a + 1) % results.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => (a - 1 + results.length) % results.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      pick(results[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="symbol-picker" ref={boxRef}>
      <input
        className="symbol-input"
        value={open ? text : display}
        placeholder="代码 / 名称 / 拼音首字母"
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
        }}
        onKeyDown={onKeyDown}
        spellCheck={false}
        autoComplete="off"
      />
      {open && (
        <div className="symbol-dropdown">
          {loading && <div className="symbol-hint">搜索中…</div>}
          {!loading && results.length === 0 && (
            <div className="symbol-hint">无匹配结果</div>
          )}
          {!loading &&
            results.map((hit, i) => (
              <div
                key={hit.code}
                className={`symbol-item ${i === active ? 'active' : ''}`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  pick(hit)
                }}
              >
                <span className="symbol-name">{hit.name}</span>
                <span className="symbol-code">{hit.code}</span>
                <span className={`symbol-type ${hit.type}`}>{TYPE_LABEL[hit.type] ?? hit.type}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
