import type { ReactNode } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";

import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

type MarkdownPageProps = {
  eyebrow: string;
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: { label: string; value: string }[];
  body: string;
};

export function MarkdownPage({ eyebrow, title, subtitle, meta, body }: MarkdownPageProps) {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <section className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-5xl px-6 py-20 lg:px-10 lg:py-24">
          <div className="space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> {eyebrow}
            </span>
            <h1 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
              {title}
            </h1>
            {subtitle ? (
              <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80 lg:text-lg lg:max-w-3xl">
                {subtitle}
              </p>
            ) : null}
          </div>
          {meta && meta.length > 0 ? (
            <dl className="mt-12 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid sm:grid-cols-2 lg:grid-cols-4">
              {meta.map((item) => (
                <div key={item.label} className="bg-landing-bg p-5">
                  <dt className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                    {item.label}
                  </dt>
                  <dd className="mt-2 font-landing-body text-sm uppercase tracking-[0.18em] text-landing-foreground">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
      </section>
      <article className="border-b border-landing-rule bg-landing-bg">
        <div className="mx-auto w-full max-w-5xl px-6 py-16 lg:px-10 lg:py-20">
          <div className="prose-doc">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSlug]}
              components={{
                h1: ({ children, ...props }) => (
                  <h2
                    {...props}
                    className="mt-16 first:mt-0 scroll-mt-24 font-landing-display text-2xl leading-tight text-landing-foreground lg:text-4xl"
                  >
                    {children}
                  </h2>
                ),
                h2: ({ children, ...props }) => (
                  <h2
                    {...props}
                    className="mt-16 first:mt-0 scroll-mt-24 font-landing-display text-2xl leading-tight text-landing-foreground lg:text-4xl"
                  >
                    {children}
                  </h2>
                ),
                h3: ({ children, ...props }) => (
                  <h3
                    {...props}
                    className="mt-12 scroll-mt-24 font-landing-display text-xl leading-tight text-landing-foreground lg:text-2xl"
                  >
                    {children}
                  </h3>
                ),
                h4: ({ children, ...props }) => (
                  <h4
                    {...props}
                    className="mt-8 scroll-mt-24 font-landing-body text-[11px] uppercase tracking-[0.3em] text-landing-alarm"
                  >
                    {children}
                  </h4>
                ),
                p: ({ children, ...props }) => (
                  <p
                    {...props}
                    className="mt-5 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85"
                  >
                    {children}
                  </p>
                ),
                ul: ({ children, ...props }) => (
                  <ul
                    {...props}
                    className="mt-5 space-y-2 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85 pl-5 list-disc marker:text-landing-alarm"
                  >
                    {children}
                  </ul>
                ),
                ol: ({ children, ...props }) => (
                  <ol
                    {...props}
                    className="mt-5 space-y-2 font-landing-body text-[15px] leading-relaxed text-landing-foreground/85 pl-5 list-decimal marker:text-landing-muted"
                  >
                    {children}
                  </ol>
                ),
                li: ({ children, ...props }) => (
                  <li {...props} className="pl-1">
                    {children}
                  </li>
                ),
                strong: ({ children, ...props }) => (
                  <strong {...props} className="font-semibold text-landing-foreground">
                    {children}
                  </strong>
                ),
                em: ({ children, ...props }) => (
                  <em {...props} className="italic text-landing-foreground/90">
                    {children}
                  </em>
                ),
                a: ({ href = "", children, ...props }) => {
                  const isInternal = href.startsWith("/") || href.startsWith("#");
                  if (isInternal) {
                    return (
                      <Link
                        href={href}
                        {...props}
                        className="border-b border-landing-alarm pb-px text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground"
                      >
                        {children}
                      </Link>
                    );
                  }
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noreferrer noopener"
                      {...props}
                      className="border-b border-landing-alarm pb-px text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground"
                    >
                      {children}
                    </a>
                  );
                },
                code: ({ className, children, ...props }) => {
                  const isBlock = (className ?? "").startsWith("language-");
                  if (isBlock) {
                    return (
                      <code
                        className="block whitespace-pre-wrap break-all font-landing-mono text-[12px] leading-relaxed text-landing-foreground/85"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code
                      className="border border-landing-rule-solid bg-landing-bg px-1.5 py-0.5 font-landing-mono text-[12px] uppercase tracking-[0.06em] text-landing-foreground/90"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                pre: ({ children, ...props }) => (
                  <pre
                    {...props}
                    className="mt-5 overflow-x-auto border border-landing-rule-solid bg-[color:var(--landing-bg-elevated,#15171c)] p-4 font-landing-mono text-[12px] leading-relaxed text-landing-foreground/85"
                  >
                    {children}
                  </pre>
                ),
                blockquote: ({ children, ...props }) => (
                  <blockquote
                    {...props}
                    className="mt-6 border-l-2 border-landing-alarm pl-5 font-landing-body text-[15px] italic leading-relaxed text-landing-foreground/85"
                  >
                    {children}
                  </blockquote>
                ),
                hr: (props) => (
                  <hr {...props} className="my-12 border-0 border-t border-landing-rule-solid" />
                ),
                table: ({ children, ...props }) => (
                  <div className="mt-6 overflow-x-auto">
                    <table
                      {...props}
                      className="w-full border-collapse border border-landing-rule-solid font-landing-body text-[13px] text-landing-foreground/85"
                    >
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children, ...props }) => (
                  <thead {...props} className="bg-[color:var(--landing-bg-elevated,#15171c)]">
                    {children}
                  </thead>
                ),
                tr: ({ children, ...props }) => (
                  <tr
                    {...props}
                    className="border-b border-landing-rule-solid last:border-b-0"
                  >
                    {children}
                  </tr>
                ),
                th: ({ children, ...props }) => (
                  <th
                    {...props}
                    className="border-r border-landing-rule-solid p-3 text-left font-landing-body text-[10px] uppercase tracking-[0.22em] text-landing-muted last:border-r-0 align-top"
                  >
                    {children}
                  </th>
                ),
                td: ({ children, ...props }) => (
                  <td
                    {...props}
                    className="border-r border-landing-rule-solid p-3 align-top last:border-r-0"
                  >
                    {children}
                  </td>
                ),
              }}
            >
              {body}
            </ReactMarkdown>
          </div>
        </div>
      </article>
      <PublicFooter />
    </main>
  );
}
