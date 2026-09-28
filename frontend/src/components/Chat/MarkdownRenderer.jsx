import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-language-tag">{language ? language.toLowerCase() : 'code'}</span>
        <button
          className="code-copy-btn"
          onClick={handleCopy}
          type="button"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check size={12} color="var(--accent-green, #10b981)" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Copy code</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-block-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function MarkdownRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="markdown-body">
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const rawCode = String(children).replace(/\n$/, '');
            const isMultiline = rawCode.includes('\n');

            if (!inline && (match || isMultiline)) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  code={rawCode}
                />
              );
            }
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
          },
          pre({ children }) {
            // Flatten pre so CodeBlock handles its own wrapper cleanly
            return <>{children}</>;
          },
          table({ children }) {
            return (
              <div className="table-responsive">
                <table className="md-table">{children}</table>
              </div>
            );
          },
          blockquote({ children }) {
            return <blockquote className="md-blockquote">{children}</blockquote>;
          },
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
                {children}
              </a>
            );
          },
          h1({ children }) {
            return <h3 className="md-h1">{children}</h3>;
          },
          h2({ children }) {
            return <h4 className="md-h2">{children}</h4>;
          },
          h3({ children }) {
            return <h5 className="md-h3">{children}</h5>;
          },
          ul({ children }) {
            return <ul className="md-ul">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="md-ol">{children}</ol>;
          },
          p({ children }) {
            return <p className="md-p">{children}</p>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
