using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Diagnostics;
using Newtonsoft.Json.Linq;
using Microsoft.AspNetCore.Http;
using System.Net.Http;

namespace FastLaneHypermarket.Controllers
{
    public class HomeController : Controller
    {
        private readonly FastLaneContext _context;
        private readonly IConfiguration _config;
        private readonly HttpClient _httpClient; // Use only one HttpClient

        public HomeController(
            FastLaneContext context,
            IHttpClientFactory httpClientFactory,
            IConfiguration config)
        {
            _context = context;
            _config = config;
            _httpClient = httpClientFactory.CreateClient(); // Remove "WeatherAPI" name for now
        }

        // ========================
        // 🏠 HOME PAGE
        // ========================
        public async Task<IActionResult> Index()
        {
            var userName = HttpContext.Session.GetString("UserName");
            ViewBag.CustomerName = userName;

            var featured = await _context.Products
                .OrderBy(r => Guid.NewGuid())
                .Take(10)
                .ToListAsync();

            return View(featured);
        }

        // ========================
        // ℹ️ ABOUT PAGE
        // ========================
        public IActionResult About()
        {
            return View();
        }

        // ========================
        // 🌦 WEATHER API - FIXED
        // ========================
        [HttpGet]
        public async Task<IActionResult> GetWeather(double lat, double lon)
        {
            try
            {
                string apiKey = _config["WeatherSettings:ApiKey"];

                // Check if API key is configured
                if (string.IsNullOrEmpty(apiKey) || apiKey == "YOUR_OPENWEATHER_API_KEY")
                {
                    return Json(new { error = "Weather service not configured." });
                }

                string url = $"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={apiKey}";

                // Use _httpClient (not _client)
                var response = await _httpClient.GetAsync(url);

                if (response.IsSuccessStatusCode)
                {
                    var result = await response.Content.ReadAsStringAsync();
                    var json = JObject.Parse(result);

                    return Json(new
                    {
                        temp = (double)json["main"]["temp"],
                        desc = (string)json["weather"][0]["description"],
                        location = (string)json["name"],
                        icon = (string)json["weather"][0]["icon"] // Added icon
                    });
                }
                else
                {
                    return Json(new { error = "Weather API returned an error." });
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Weather API error: {ex.Message}");
                return Json(new { error = "Unable to fetch weather data." });
            }
        }

        // ========================
        // 📞 CONTACT PAGE
        // ========================
        public IActionResult Contact()
        {
            return View();
        }

        // ========================
        // 🛍️ PRODUCTS PAGE
        // ========================
        public async Task<IActionResult> Products()
        {
            try
            {
                var products = await _context.Products
                    .Where(p => p.ProductStatus == "Active" || p.ProductStatus == "Out of Stock")
                    .OrderBy(p => p.ProductName)
                    .Select(p => new Product
                    {
                        ProductCode = p.ProductCode,
                        ProductName = p.ProductName,
                        Category = p.Category,
                        SellingPrice = p.SellingPrice,
                        Quantity = p.Quantity,
                        ProductStatus = p.ProductStatus,
                        ImageUrl = p.ImageUrl ?? "/images/products/default.jpg"
                    })
                    .ToListAsync();

                if (!products.Any())
                {
                    ViewBag.Message = "No products available right now.";
                }

                return View(products);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"❌ Products() error: {ex.Message}");
                TempData["ErrorMessage"] = "Error loading products.";
                return View(new List<Product>());
            }
        }

        // ========================
        // 📋 PRODUCT DETAILS PAGE
        // ========================
        public IActionResult Details(int id)
        {
            try
            {
                var product = _context.Products.FirstOrDefault(p => p.ProductCode == id);
                if (product == null)
                {
                    TempData["Error"] = "Product not found.";
                    return RedirectToAction("Products");
                }
                return View("ProductDetails", product);
            }
            catch
            {
                TempData["Error"] = "Error loading product details.";
                return RedirectToAction("Products");
            }
        }

        // ========================
        // 🛒 CART PAGE
        // ========================
        public async Task<IActionResult> Cart()
        {
            var customerId = HttpContext.Session.GetInt32("CustomerId");

            if (!customerId.HasValue)
                return RedirectToAction("Login", "Account");

            var cartItems = await _context.CartItems
                .Where(c => c.CustomerId == customerId.Value)
                .Include(c => c.Product)
                .ToListAsync();

            return View(cartItems);
        }

        // ========================
        // 🗺️ LOCATION PAGE
        // ========================
        public IActionResult Location()
        {
            return View();
        }
    }
}