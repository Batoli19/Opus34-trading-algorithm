using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Diagnostics;

namespace FastLaneHypermarket.Controllers
{
    public class StaffController : Controller
    {
        private readonly FastLaneContext _context;
        private readonly IWebHostEnvironment _environment;

        public StaffController(FastLaneContext context, IWebHostEnvironment environment)
        {
            _context = context;
            _environment = environment;
        }

        // ✅ STAFF DASHBOARD
        public IActionResult Dashboard()
        {
            try
            {
                // Simple, safe summary data
                ViewBag.TotalProducts = _context.Products.Count();
                ViewBag.TotalCustomers = _context.Customers.Count();
                ViewBag.TotalStaff = _context.Staff.Count();

                // ✅ FIXED: Calculate total revenue from transactions
                // Use Price * Quantity since Amount is computed
                ViewBag.TotalSales = _context.Transactions
                    .Sum(t => t.Price * t.Quantity);

                // Recent customers (safe projection)
                ViewBag.RecentCustomers = _context.Customers
                    .OrderByDescending(c => c.CustomerId)
                    .Take(5)
                    .Select(c => new
                    {
                        Firstname = c.Firstname ?? "Unknown",
                        Surname = c.Surname ?? "",
                        Email = c.Email ?? "No email",
                        CustomerStatus = c.CustomerStatus ?? "Active"
                    })
                    .ToList();

                // Recent staff (safe projection)
                ViewBag.RecentStaff = _context.Staff
                    .OrderByDescending(s => s.StaffId)
                    .Take(5)
                    .Select(s => new
                    {
                        Firstname = s.Firstname ?? "Unknown",
                        Surname = s.Surname ?? "",
                        Role = s.Role ?? "Staff",
                        StaffStatus = s.StaffStatus ?? "Active"
                    })
                    .ToList();

                return View();
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Dashboard error: {ex.Message}");

                // Fallback defaults
                ViewBag.TotalProducts = 0;
                ViewBag.TotalCustomers = 0;
                ViewBag.TotalStaff = 0;
                ViewBag.TotalSales = 0; // ✅ Added fallback for sales
                ViewBag.RecentCustomers = new List<object>();
                ViewBag.RecentStaff = new List<object>();

                return View();
            }
        }
        // ✅ PRODUCTS MANAGEMENT
        public IActionResult StaffProducts()
        {
            var products = _context.Products.ToList();
            Debug.WriteLine($"Loaded {products.Count} products from DB");
            return View("~/Views/Staff/StaffProducts.cshtml", products);
        }

        // ✅ ADD PRODUCT WITH IMAGE UPLOAD
        [HttpPost]
        [ValidateAntiForgeryToken]
        public IActionResult AddProduct(Product product, IFormFile imageFile)
        {
            try
            {
                Console.WriteLine("=== ADD PRODUCT STARTED ===");
                Console.WriteLine($"Product Name: {product.ProductName}");
                Console.WriteLine($"Category: {product.Category}");
                Console.WriteLine($"Quantity: {product.Quantity}");
                Console.WriteLine($"PurchasePrice: {product.PurchasePrice}");
                Console.WriteLine($"ModelState IsValid: {ModelState.IsValid}");

                // Set the required fields that aren't in the form
                product.ImageUrl = "/images/products/default.jpg"; // Default image
                product.ProductStatus = "Active"; // Default status
                product.RecordedBy = User.Identity?.Name ?? "Staff"; // Current user or default
                product.DatePurchased = DateTime.Now; // Current date

                // Handle image upload if provided
                if (imageFile != null && imageFile.Length > 0)
                {
                    Console.WriteLine($"Image file received: {imageFile.FileName}, Size: {imageFile.Length}");
                    var uploadsFolder = Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "images", "products");
                    if (!Directory.Exists(uploadsFolder))
                        Directory.CreateDirectory(uploadsFolder);

                    var uniqueFileName = Guid.NewGuid().ToString() + "_" + imageFile.FileName;
                    var filePath = Path.Combine(uploadsFolder, uniqueFileName);

                    using (var fileStream = new FileStream(filePath, FileMode.Create))
                    {
                        imageFile.CopyTo(fileStream);
                    }

                    product.ImageUrl = "/images/products/" + uniqueFileName;
                }

                // Calculate selling price
                product.SellingPrice = product.PurchasePrice * (1 + (decimal)(product.PercentageMarkup / 100));

                // Clear ModelState and re-validate since we've set the required fields
                ModelState.Clear();
                TryValidateModel(product);

                if (ModelState.IsValid)
                {
                    Console.WriteLine($"Saving product to database...");
                    _context.Products.Add(product);
                    _context.SaveChanges();

                    Console.WriteLine("=== PRODUCT SAVED SUCCESSFULLY ===");
                    TempData["Success"] = $"Product '{product.ProductName}' added successfully!";
                    return RedirectToAction("StaffProducts");
                }
                else
                {
                    Console.WriteLine("=== MODEL STATE INVALID ===");

                    // Log the specific errors
                    foreach (var error in ModelState.Values.SelectMany(v => v.Errors))
                    {
                        Console.WriteLine($"ModelError: {error.ErrorMessage}");
                    }

                    TempData["Error"] = "Please fix the validation errors: " +
                        string.Join(", ", ModelState.Values
                            .SelectMany(v => v.Errors)
                            .Select(e => e.ErrorMessage));
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"=== EXCEPTION: {ex.Message} ===");
                Console.WriteLine($"Stack Trace: {ex.StackTrace}");
                TempData["Error"] = $"Error adding product: {ex.Message}";
            }

            return RedirectToAction("StaffProducts");
        }
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> DeleteProduct(int productCode)
        {
            try
            {
                var product = await _context.Products.FindAsync(productCode);
                if (product == null)
                {
                    TempData["ErrorMessage"] = "❌ Product not found.";
                    return RedirectToAction("StaffProducts");
                }

                // Delete associated image file if exists
                if (!string.IsNullOrEmpty(product.ImageUrl) && product.ImageUrl != "/images/products/default.jpg")
                {
                    var imagePath = Path.Combine(_environment.WebRootPath, product.ImageUrl.TrimStart('/'));
                    if (System.IO.File.Exists(imagePath))
                    {
                        System.IO.File.Delete(imagePath);
                    }
                }

                _context.Products.Remove(product);
                await _context.SaveChangesAsync();

                TempData["SuccessMessage"] = $"✅ Product '{product.ProductName}' deleted successfully!";
                return RedirectToAction("StaffProducts");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error deleting product: {ex.Message}");
                TempData["ErrorMessage"] = "❌ Error deleting product.";
                return RedirectToAction("StaffProducts");
            }
        }

        // ✅ EDIT PRODUCT
        public IActionResult EditProduct(int productCode)
        {
            try
            {
                var product = _context.Products.Find(productCode);
                if (product == null)
                {
                    TempData["ErrorMessage"] = "❌ Product not found.";
                    return RedirectToAction("StaffProducts");
                }
                return View(product);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error loading product for edit: {ex.Message}");
                TempData["ErrorMessage"] = "❌ Error loading product.";
                return RedirectToAction("StaffProducts");
            }
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> EditProduct(int productCode, Product product, IFormFile imageFile)
        {
            if (productCode != product.ProductCode)
            {
                TempData["ErrorMessage"] = "❌ Product ID mismatch.";
                return RedirectToAction("StaffProducts");
            }

            if (!ModelState.IsValid)
                return View(product);

            try
            {
                var existingProduct = await _context.Products.FindAsync(productCode);
                if (existingProduct == null)
                {
                    TempData["ErrorMessage"] = "❌ Product not found.";
                    return RedirectToAction("StaffProducts");
                }

                // Handle image upload
                if (imageFile != null && imageFile.Length > 0)
                {
                    var uploadsFolder = Path.Combine(_environment.WebRootPath, "images", "products");
                    if (!Directory.Exists(uploadsFolder))
                        Directory.CreateDirectory(uploadsFolder);

                    var uniqueFileName = Guid.NewGuid().ToString() + Path.GetExtension(imageFile.FileName);
                    var filePath = Path.Combine(uploadsFolder, uniqueFileName);

                    using (var fileStream = new FileStream(filePath, FileMode.Create))
                    {
                        await imageFile.CopyToAsync(fileStream);
                    }

                    // Delete old image if it exists and is not the default
                    if (!string.IsNullOrEmpty(existingProduct.ImageUrl) &&
                        existingProduct.ImageUrl != "/images/products/default.jpg")
                    {
                        var oldImagePath = Path.Combine(_environment.WebRootPath, existingProduct.ImageUrl.TrimStart('/'));
                        if (System.IO.File.Exists(oldImagePath))
                        {
                            System.IO.File.Delete(oldImagePath);
                        }
                    }

                    existingProduct.ImageUrl = $"/images/products/{uniqueFileName}";
                }

                // Update product fields
                existingProduct.ProductName = product.ProductName;
                existingProduct.Size = product.Size;
                existingProduct.Category = product.Category;
                existingProduct.Quantity = product.Quantity;
                existingProduct.ReorderLevel = product.ReorderLevel;
                existingProduct.PurchasePrice = product.PurchasePrice;
                existingProduct.PercentageMarkup = product.PercentageMarkup;
                existingProduct.SellingPrice = product.PurchasePrice * (1 + (decimal)(product.PercentageMarkup / 100));
                existingProduct.ProductStatus = product.Quantity > 0 ? "Active" : "Out of Stock";

                await _context.SaveChangesAsync();

                TempData["SuccessMessage"] = $"✅ Product '{product.ProductName}' updated successfully!";
                return RedirectToAction("StaffProducts");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"EditProduct Save Error: {ex.Message}");
                TempData["ErrorMessage"] = $"❌ Error updating product: {ex.Message}";
                return View(product);
            }
        }

        // ✅ SIMPLE VIEWS
        public IActionResult Staff()
        {
            var staff = _context.Staff.ToList();
            return View(staff);
        }
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> ToggleStaffStatus(int id)
        {
            try
            {
                var staff = await _context.Staff.FindAsync(id);
                if (staff == null)
                {
                    TempData["Error"] = "Staff member not found.";
                    return RedirectToAction(nameof(Staff));
                }

                // Toggle status
                staff.StaffStatus = staff.StaffStatus == "Active" ? "Inactive" : "Active";
                _context.Staff.Update(staff);
                await _context.SaveChangesAsync();

                var action = staff.StaffStatus == "Active" ? "activated" : "deactivated";
                TempData["Success"] = $"{staff.Firstname} {staff.Surname} has been {action} successfully.";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error updating staff status: {ex.Message}";
            }

            return RedirectToAction(nameof(Staff));
        }


        public IActionResult Customers()
        {
            var customers = _context.Customers.ToList();
            return View(customers);
        }

        // Add the missing action methods here:
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> ActivateCustomer(int id)
        {
            try
            {
                var customer = await _context.Customers.FindAsync(id);
                if (customer == null)
                {
                    TempData["Error"] = "Customer not found.";
                    return RedirectToAction(nameof(Customers));
                }

                customer.CustomerStatus = "Active";
                _context.Customers.Update(customer);
                await _context.SaveChangesAsync();

                TempData["Success"] = $"{customer.FullName} has been activated successfully.";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error activating customer: {ex.Message}";
            }

            return RedirectToAction(nameof(Customers));
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> DeactivateCustomer(int id)
        {
            try
            {
                var customer = await _context.Customers.FindAsync(id);
                if (customer == null)
                {
                    TempData["Error"] = "Customer not found.";
                    return RedirectToAction(nameof(Customers));
                }

                customer.CustomerStatus = "Inactive";
                _context.Customers.Update(customer);
                await _context.SaveChangesAsync();

                TempData["Success"] = $"{customer.FullName} has been deactivated.";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error deactivating customer: {ex.Message}";
            }

            return RedirectToAction(nameof(Customers));
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> BlacklistCustomer(int id)
        {
            try
            {
                var customer = await _context.Customers.FindAsync(id);
                if (customer == null)
                {
                    TempData["Error"] = "Customer not found.";
                    return RedirectToAction(nameof(Customers));
                }

                customer.CustomerStatus = "Blacklisted";
                _context.Customers.Update(customer);
                await _context.SaveChangesAsync();

                TempData["Success"] = $"{customer.FullName} has been blacklisted.";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error blacklisting customer: {ex.Message}";
            }

            return RedirectToAction(nameof(Customers));
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> UpdateCustomerStatus(int id, string status)
        {
            try
            {
                var customer = await _context.Customers.FindAsync(id);
                if (customer == null)
                {
                    TempData["Error"] = "Customer not found.";
                    return RedirectToAction(nameof(Customers));
                }

                // Validate the status
                var validStatuses = new[] { "Active", "Inactive", "Blacklisted" };
                if (!validStatuses.Contains(status))
                {
                    TempData["Error"] = "Invalid status provided.";
                    return RedirectToAction(nameof(Customers));
                }

                customer.CustomerStatus = status;
                _context.Customers.Update(customer);
                await _context.SaveChangesAsync();

                TempData["Success"] = $"{customer.FullName}'s status has been updated to {status}.";
            }
            catch (Exception ex)
            {
                TempData["Error"] = $"Error updating customer status: {ex.Message}";
            }

            return RedirectToAction(nameof(Customers));
        }

        public async Task<IActionResult> Sales()
        {
            var transactions = await _context.Transactions
                .Include(t => t.Customer)
                .Include(t => t.Product)
                .ToListAsync();

            return View(transactions);
        }

        public IActionResult Reports() => View();
        public IActionResult Settings() => View();
    }
}
