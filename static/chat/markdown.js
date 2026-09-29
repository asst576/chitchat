(() => {
  const safeLinkSchemes = new Set(["http", "https", "mailto"]);

  function safeHref(value) {
    const href = value.trim();
    if (!href || /[\u0000-\u001f\u007f\\]/.test(href) || href.startsWith("//")) return null;
    const scheme = href.match(/^([a-z][a-z\d+.-]*):/i)?.[1].toLowerCase();
    return scheme && !safeLinkSchemes.has(scheme) ? null : href;
  }

  function parseInline(source, allowLinks = true) {
    const nodes = [];
    let text = "";
    const flush = () => {
      if (!text) return;
      nodes.push({ type: "text", text });
      text = "";
    };

    for (let index = 0; index < source.length;) {
      if (source[index] === "`") {
        const end = source.indexOf("`", index + 1);
        if (end > index + 1) {
          flush();
          nodes.push({ type: "code", text: source.slice(index + 1, end) });
          index = end + 1;
          continue;
        }
      }

      const strongMarker = source.startsWith("**", index)
        ? "**"
        : source.startsWith("__", index) ? "__" : "";
      if (strongMarker) {
        const end = source.indexOf(strongMarker, index + 2);
        if (end > index + 2) {
          flush();
          nodes.push({ type: "strong", children: parseInline(source.slice(index + 2, end), allowLinks) });
          index = end + 2;
          continue;
        }
      }

      if (source[index] === "*" || source[index] === "_") {
        const marker = source[index];
        const end = source.indexOf(marker, index + 1);
        if (end > index + 1 && source[index + 1] !== " " && source[end - 1] !== " ") {
          flush();
          nodes.push({ type: "emphasis", children: parseInline(source.slice(index + 1, end), allowLinks) });
          index = end + 1;
          continue;
        }
      }

      if (allowLinks && source[index] === "!" && source[index + 1] === "[") {
        const closeLabel = source.indexOf("]", index + 2);
        const closeUrl = closeLabel >= 0 && source[closeLabel + 1] === "("
          ? source.indexOf(")", closeLabel + 2)
          : -1;
        if (closeUrl >= 0) {
          text += source.slice(index, closeUrl + 1);
          index = closeUrl + 1;
          continue;
        }
      }

      if (allowLinks && source[index] === "[") {
        const closeLabel = source.indexOf("]", index + 1);
        const closeUrl = closeLabel >= 0 && source[closeLabel + 1] === "("
          ? source.indexOf(")", closeLabel + 2)
          : -1;
        if (closeUrl >= 0) {
          const raw = source.slice(closeLabel + 2, closeUrl);
          const href = safeHref(raw);
          flush();
          if (href) {
            nodes.push({
              type: "link",
              href,
              children: parseInline(source.slice(index + 1, closeLabel), false),
            });
          } else {
            nodes.push({ type: "text", text: source.slice(index, closeUrl + 1) });
          }
          index = closeUrl + 1;
          continue;
        }
      }

      text += source[index];
      index += 1;
    }

    flush();
    return nodes;
  }

  function listMarker(line) {
    const unordered = line.match(/^\s{0,3}[-+*]\s+(.*)$/);
    if (unordered) return { type: "unordered-list", item: unordered[1] };
    const ordered = line.match(/^\s{0,3}\d+[.)]\s+(.*)$/);
    return ordered ? { type: "ordered-list", item: ordered[1] } : null;
  }

  function startsBlock(line) {
    return /^\s{0,3}```/.test(line)
      || /^\s{0,3}#{1,6}(?:\s|$)/.test(line)
      || listMarker(line) !== null;
  }

  function parse(markdown) {
    const lines = String(markdown ?? "").replace(/\r\n?/g, "\n").split("\n");
    const blocks = [];
    let index = 0;

    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) {
        index += 1;
        continue;
      }

      if (/^\s{0,3}```/.test(line)) {
        const code = [];
        index += 1;
        while (index < lines.length && !/^\s{0,3}```\s*$/.test(lines[index])) {
          code.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) index += 1;
        blocks.push({ type: "code-block", text: code.join("\n") });
        continue;
      }

      const heading = line.match(/^\s{0,3}(#{1,6})(?:\s+|$)(.*?)\s*#*\s*$/);
      if (heading) {
        blocks.push({
          type: "heading",
          level: heading[1].length,
          children: parseInline(heading[2]),
        });
        index += 1;
        continue;
      }

      const marker = listMarker(line);
      if (marker) {
        const items = [];
        const listType = marker.type;
        while (index < lines.length) {
          const current = listMarker(lines[index]);
          if (!current || current.type !== listType) break;
          items.push(parseInline(current.item));
          index += 1;
        }
        blocks.push({ type: listType, items });
        continue;
      }

      const paragraph = [line];
      index += 1;
      while (index < lines.length && lines[index].trim() && !startsBlock(lines[index])) {
        paragraph.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: "paragraph", children: parseInline(paragraph.join(" ")) });
    }

    return blocks;
  }

  function appendInline(parent, nodes) {
    for (const node of nodes) {
      if (node.type === "text") {
        parent.appendChild(document.createTextNode(node.text));
        continue;
      }

      const tag = {
        code: "code",
        emphasis: "em",
        link: "a",
        strong: "strong",
      }[node.type];
      const element = document.createElement(tag);
      if (node.type === "link") {
        element.setAttribute("href", node.href);
        element.setAttribute("target", "_blank");
        element.setAttribute("rel", "noopener noreferrer");
      }
      if (node.type === "code") {
        element.appendChild(document.createTextNode(node.text));
      } else {
        appendInline(element, node.children);
      }
      parent.appendChild(element);
    }
  }

  function render(markdown) {
    const fragment = document.createDocumentFragment();
    for (const block of parse(markdown)) {
      if (block.type === "code-block") {
        const pre = document.createElement("pre");
        const code = document.createElement("code");
        code.appendChild(document.createTextNode(block.text));
        pre.appendChild(code);
        fragment.appendChild(pre);
        continue;
      }

      if (block.type === "unordered-list" || block.type === "ordered-list") {
        const list = document.createElement(block.type === "unordered-list" ? "ul" : "ol");
        for (const item of block.items) {
          const li = document.createElement("li");
          appendInline(li, item);
          list.appendChild(li);
        }
        fragment.appendChild(list);
        continue;
      }

      const element = document.createElement(block.type === "heading" ? "h" + block.level : "p");
      appendInline(element, block.children);
      fragment.appendChild(element);
    }
    return fragment;
  }

  window.ChatMarkdown = { parse, render };
})();
