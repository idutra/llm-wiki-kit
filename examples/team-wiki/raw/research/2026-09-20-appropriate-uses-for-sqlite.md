---
source_url: https://sqlite.org/whentouse.html
collected: 2026-09-20
published: 2025-05-31
author: SQLite project
title: Appropriate Uses For SQLite
found_by: research
research_question: wiki/questions/sqlite-em-producao.md
angle: contrarian
capture: partial
---

> Captura parcial: só os trechos que respondem à pergunta. A página completa está na URL acima.
> Texto de terceiros, reproduzido aqui como evidência citável.

## Situations Where A Client/Server RDBMS May Work Better

**High Concurrency.** SQLite supports an unlimited number of simultaneous readers, but it will only allow
one writer at any instant in time. For many situations, this is not a problem. Writers queue up. Each
application does its database work quickly and moves on, and no lock lasts for more than a few dozen
milliseconds. But there are some applications that require more concurrency, and those applications may
need to seek a different solution.

## Websites

SQLite works great as the database engine for most low to medium traffic websites (which is to say, most
websites). [...] If the website is write-intensive or is so busy that it requires multiple servers, then
consider using an enterprise-class client/server database engine instead of SQLite.
