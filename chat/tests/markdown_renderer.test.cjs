const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class TestNode {
  constructor(tagName, text = "") {
    this.tagName = tagName;
    this.text = text;
    this.children = [];
    this.attributes = {};
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  setAttribute(name, value) {
    this.attributes[name] = value;
  }
}

const document = {
  createDocumentFragment: () => new TestNode("#fragment"),
  createElement: (tagName) => new TestNode(tagName),
  createTextNode: (text) => new TestNode("#text", String(text)),
};
const window = {};
const source = fs.readFileSync(path.resolve(__dirname, "../../static/chat/markdown.js"), "utf8");
vm.runInNewContext(source, { document, window });
const markdown = window.ChatMarkdown;
const normalize = (value) => JSON.parse(JSON.stringify(value));

const blocks = normalize(markdown.parse(
  "**bold** and *italic* with `inline code` and [a link](https://example.test/path)\n\n"
  + "## Heading\n\n- bullet item\n- second bullet\n\n1. numbered item\n2. second number\n\n"
  + "```js\nconst answer = 42;\n```",
));
assert.equal(blocks[0].type, "paragraph");
assert.ok(blocks[0].children.some((node) => node.type === "strong"));
assert.ok(blocks[0].children.some((node) => node.type === "emphasis"));
assert.ok(blocks[0].children.some((node) => node.type === "code"));
assert.ok(blocks[0].children.some((node) => node.type === "link"));
assert.deepEqual(blocks.map((block) => block.type), [
  "paragraph",
  "heading",
  "unordered-list",
  "ordered-list",
  "code-block",
]);
assert.equal(blocks[1].level, 2);
assert.equal(blocks[2].items.length, 2);
assert.equal(blocks[3].items.length, 2);
assert.equal(blocks[4].text, "const answer = 42;");

const unsafe = normalize(markdown.parse(
  "<img src=x onerror=alert(1)> [run](javascript:alert(1)) [safe](https://example.test)",
));
const rendered = markdown.render("<img src=x onerror=alert(1)> [run](javascript:alert(1)) [safe](https://example.test)");
const allowedTags = new Set(["#fragment", "#text", "p", "a", "strong", "em", "code", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "pre"]);
const nodes = [];
function visit(node) {
  nodes.push(node);
  assert.ok(allowedTags.has(node.tagName), "unexpected rendered element: " + node.tagName);
  for (const name of Object.keys(node.attributes)) {
    assert.ok(["href", "target", "rel"].includes(name), "unexpected rendered attribute: " + name);
    assert.ok(!name.toLowerCase().startsWith("on"));
  }
  node.children.forEach(visit);
}
function textContent(node) {
  return node.tagName === "#text" ? node.text : node.children.map(textContent).join("");
}
visit(rendered);
assert.ok(unsafe[0].children.some((node) => node.type === "text" && node.text.includes("<img src=x onerror=alert(1)>")));
assert.ok(textContent(rendered).includes("[run](javascript:alert(1))"));
assert.ok(nodes.some((node) => node.tagName === "a" && node.attributes.href === "https://example.test"));
assert.ok(!nodes.some((node) => node.tagName === "script" || node.tagName === "img"));
assert.ok(!source.includes("innerHTML"));
process.stdout.write("Markdown parser/render safety checks passed.\n");
