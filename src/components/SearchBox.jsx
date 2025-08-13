import { useMemo, useState } from "react";
import { useStore } from "../store";

export default function SearchBox({ fuse }) {
  const {
    query,
    setQuery,
    activeIndex,
    setActiveIndex,
    setSelectedId,
  } = useStore();
  const [open, setOpen] = useState(false);

  const results = useMemo(() => {
    if (!fuse || query.length < 2) return [];
    return fuse.search(query).slice(0, 8);
  }, [fuse, query]);

  const showDropdown = open && query.length >= 2;

  const handleSelect = (feature) => {
    setSelectedId(feature.properties.id);
    setQuery(feature.properties.name);
    setActiveIndex(-1);
    setOpen(false);
  };

  return (
    <div style={{ position: "relative" }}>
      <input
        value={query}
        placeholder="Search buildings…"
        onChange={(e) => {
          const v = e.target.value;
          setQuery(v);
          setActiveIndex(-1);
          setOpen(v.length >= 2);
        }}
        onKeyDown={(e) => {
          if (!showDropdown) {
            if (e.key === "Escape") {
              setQuery("");
              setActiveIndex(-1);
              setOpen(false);
            }
            return;
          }
          if (results.length === 0) {
            if (e.key === "Escape") {
              setQuery("");
              setActiveIndex(-1);
              setOpen(false);
            }
            return;
          }
          if (e.key === "ArrowDown") {
            e.preventDefault();
            const next = (activeIndex + 1) % results.length;
            setActiveIndex(next);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            const next = (activeIndex - 1 + results.length) % results.length;
            setActiveIndex(next);
          } else if (e.key === "Enter") {
            e.preventDefault();
            const sel =
              results[activeIndex >= 0 ? activeIndex : 0];
            if (sel) handleSelect(sel.item);
          } else if (e.key === "Escape") {
            setQuery("");
            setActiveIndex(-1);
            setOpen(false);
          }
        }}
        aria-activedescendant={
          activeIndex >= 0 ? `search-option-${activeIndex}` : undefined
        }
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 8,
          border: "1px solid #ccd",
        }}
      />
      {showDropdown && (
        <ul
          role="listbox"
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "#fff",
            border: "1px solid #ccd",
            borderRadius: 8,
            margin: 0,
            padding: 0,
            listStyle: "none",
            maxHeight: 240,
            overflowY: "auto",
            zIndex: 10,
          }}
        >
          {results.length > 0 ? (
            results.map((r, i) => (
              <li
                key={r.item.properties.id}
                id={`search-option-${i}`}
                role="option"
                aria-selected={activeIndex === i}
                style={{
                  padding: "6px 8px",
                  background: activeIndex === i ? "#e1e9ff" : "#fff",
                  cursor: "pointer",
                }}
                onMouseDown={() => handleSelect(r.item)}
              >
                {r.item.properties.name}
              </li>
            ))
          ) : (
            <li style={{ padding: "6px 8px", color: "#777" }}>No results</li>
          )}
        </ul>
      )}
    </div>
  );
}

