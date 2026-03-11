using FastLaneHypermarket.Models;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// ✅ Configure EF Core connection
builder.Services.AddDbContext<FastLaneContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("FastLaneDB")));

// ✅ Add MVC, session, and context accessor
builder.Services.AddControllersWithViews();
builder.Services.AddSession();
builder.Services.AddHttpContextAccessor();

var app = builder.Build();

// ✅ Ensure static files (CSS, JS, images) are served
app.UseStaticFiles();

// ✅ Use session
app.UseSession();

// ✅ Enable routing and authorization
app.UseRouting();
app.UseAuthorization();

// ✅ Map default route
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");


app.Run();
