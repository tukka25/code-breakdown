# Finding the handler for an endpoint

Search for the path's last fixed segment as a string, then confirm the method and any prefix the router is mounted under. Paths are often split: a router or controller adds a prefix, and the route adds the rest.

Start with a search such as `grep -rn '"/orders' --include='*.py' .` (swap the extension, and keep the quotes so the shell does not expand the glob), and read the route file it finds.

| Framework | What the route looks like | Prefix to check |
|---|---|---|
| FastAPI | `@router.post("/orders")`, `@app.post(...)` | `APIRouter(prefix=...)`, `app.include_router(router, prefix=...)` |
| Flask | `@app.route("/orders", methods=["POST"])`, `@bp.post("/orders")` | `Blueprint(..., url_prefix=...)`, `register_blueprint(..., url_prefix=...)` |
| Django | `path("orders/", views.create_order)` in `urls.py` | `include()` in the project `urls.py`. DRF: `router.register("orders", OrderViewSet)` sends POST to `create` |
| Express | `router.post("/orders", handler)`, `app.post(...)` | `app.use("/api", router)` |
| NestJS | `@Post()` on a method of `@Controller("orders")` | global prefix in `main.ts` |
| Next.js | `export async function POST` in `app/api/orders/route.ts`; `pages/api/orders.ts` default export | folder path is the URL |
| Spring | `@PostMapping("/orders")`, `@RequestMapping(method = POST)` | class-level `@RequestMapping("/api")` |
| Rails | `resources :orders` (POST goes to `OrdersController#create`), `post "/orders", to: "orders#create"` | `namespace`, `scope` in `routes.rb` |
| Laravel | `Route::post('/orders', [OrderController::class, 'store'])` | `Route::prefix()`, `routes/api.php` adds `/api` |
| Go | `mux.HandleFunc("POST /orders", h)`, gin `r.POST`, chi `r.Post`, echo `e.POST` | `r.Group(...)`, `r.Route(...)`, `http.StripPrefix` |
| ASP.NET | `[HttpPost("orders")]` in `[Route("api/[controller]")]`; minimal API `app.MapPost("/orders", ...)` | `MapGroup(...)` |
| Phoenix | `post "/orders", OrderController, :create` in `router.ex` | `scope "/api"` |

## What to include

- **The handler is the entry block.** Include its decorator or annotation; the check pulls in lines directly above it.
- **Dependencies the route declares** that live in the repository are code blocks called from the handler. Examples: FastAPI `Depends(get_db)`, NestJS guards and pipes, Express middleware in the route's own chain. Their name appears in the handler's lines, so the arrow checks out.
- **Request and response models** are `type` blocks.
- **The data the handler reaches:** services, repositories, queries, ORM models.

Global middleware that runs for every route is not part of this endpoint's story. Leave it out.

## Anonymous handlers

When the handler is an inline function, give the block an id you make up and a `name` that appears on its first line:

```json
{"id": "post_orders", "name": "post", "file": "src/routes/orders.ts", "start": 12, "end": 40, "label": "Entry point"}
```
