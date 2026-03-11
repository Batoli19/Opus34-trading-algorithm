using FastLaneHypermarket.Models;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// EF Core
builder.Services.AddDbContext<FastLaneContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("FastLaneDB")));

builder.Services.AddControllersWithViews();
builder.Services.AddSession();
builder.Services.AddHttpContextAccessor();

// ✅ REGISTER HttpClient
builder.Services.AddHttpClient(); // This is correct

var app = builder.Build();

app.UseStaticFiles();
app.UseSession();
app.UseRouting();
app.UseAuthorization();

app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();