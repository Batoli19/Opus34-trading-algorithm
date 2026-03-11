using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Diagnostics;

namespace FastLaneHypermarket.Controllers
{
    public class HomeController : Controller
    {
        private readonly FastLaneContext _context;

        public HomeController(FastLaneContext context)
        {
            _context = context;
        }

        // ========================
        // 🏠 HOME PAGE
        // ========================
        public async Task<IActionResult> Index()
        {
            var userName = HttpContext.Session.GetString("UserName");
            ViewBag.CustomerName = userName;

            // Random 10 products
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
        // 📞 CONTACT PAGE
        // ========================
        public IActionResult Contact()
        {
            return View();
        }

        // ========================
        // 🗺️ LOCATION PAGE
        // ========================
        public IActionResult Location()
        {
            return View();
        }

        // ========================
        // 🌤️ WEATHER PAGE
        // ========================
        public IActionResult Weather()
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
                if (_context == null)
                {
                    Debug.WriteLine("⚠️ _context is null — check dependency injection setup.");
                    return Problem("Database connection not initialized.");
                }

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

                if (products == null || !products.Any())
                {
                    ViewBag.Message = "No products available at the moment.";
                    return View(new List<Product>());
                }

                return View(products);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"❌ Products() error: {ex.Message}");
                TempData["ErrorMessage"] = "Error loading products. Please try again later.";
                return View(new List<Product>());
            }
        }

        // ========================
        // 📋 PRODUCT DETAILS PAGE
        // ========================


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
                return View("ProductDetails", product); // Specify the view name
            }
            catch (Exception ex)
            {
                TempData["Error"] = "Error loading product details.";
                return RedirectToAction("Products");
            }
        }
        public async Task<IActionResult> Cart()
        {
            var customerId = HttpContext.Session.GetInt32("CustomerId");

            if (!customerId.HasValue)
            {
                return RedirectToAction("Login", "Account");
            }

            var cartItems = await _context.CartItems
                .Where(c => c.CustomerId == customerId.Value)
                .Include(c => c.Product)
                .ToListAsync();

            return View(cartItems);
        }



    }
}
