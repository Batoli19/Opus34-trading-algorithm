using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Http;
using System.Linq;

namespace FastLaneHypermarket.Controllers
{
    public class CartController : Controller
    {
        private readonly FastLaneContext _context;

        public CartController(FastLaneContext context)
        {
            _context = context;
        }
        [HttpPost]
        public async Task<IActionResult> Checkout()
        {
            var customerId = HttpContext.Session.GetInt32("CustomerId");

            if (!customerId.HasValue)
            {
                return Json(new { success = false, message = "Please log in first." });
            }

            // Load cart items
            var cartItems = await _context.CartItems
                .Where(c => c.CustomerId == customerId.Value)
                .Include(c => c.Product)
                .ToListAsync();

            if (cartItems == null || !cartItems.Any())
            {
                return Json(new { success = false, message = "Your cart is empty." });
            }

            // Save each cart item as its own transaction record
            foreach (var item in cartItems)
            {
                var transaction = new Transaction
                {
                    CustomerId = customerId.Value,
                    ProductId = item.ProductId,
                    Quantity = item.Quantity,
                    Price = item.Product.SellingPrice
                };

                _context.Transactions.Add(transaction);
            }

            // Remove cart items after checkout
            _context.CartItems.RemoveRange(cartItems);

            await _context.SaveChangesAsync();

            return Json(new { success = true, message = "Transaction Successful!" });
        }


        [HttpPost]
        public async Task<IActionResult> AddToCart(int productId)
        {
            var customerId = HttpContext.Session.GetInt32("CustomerId");

            if (!customerId.HasValue)
            {
                return Json(new { requiresLogin = true });
            }

            // Check if product exists
            var product = await _context.Products.FindAsync(productId);
            if (product == null)
            {
                return Json(new { success = false, message = "Product not found." });
            }

            // Check if item already exists in cart
            var existingItem = await _context.CartItems
                .FirstOrDefaultAsync(c => c.CustomerId == customerId.Value && c.ProductId == productId);

            if (existingItem != null)
            {
                existingItem.Quantity++;
            }
            else
            {
                _context.CartItems.Add(new FastLaneHypermarket.Models.CartItem
                {
                    ProductId = productId,
                    CustomerId = customerId.Value,
                    Quantity = 1
                });
            }
            
        

        await _context.SaveChangesAsync();

            return Json(new { success = true, message = "Added to cart!" });
        }
        
        public IActionResult Cart()
        {
            return View();
        }


    }
}