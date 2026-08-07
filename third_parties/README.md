# third_parties/

Vendored or purchased Odoo modules not authored by Elewa -- OCA modules,
Odoo Apps Store purchases, or any other external addon this repo depends on
but doesn't own. Nothing lives here yet; this root exists so that when one
is added, it has an addons-path root that doesn't imply Elewa authorship,
rather than landing in `shared/`, `product/`, or `custom/` by default.

Anything added here should be checked in as received (or pinned via a
subtree/submodule, if the vendor's own repo is used directly) -- not
modified in place. A local fork of a third-party module belongs in its own
clearly-named root instead, so it's obvious at a glance that it diverges
from upstream.
