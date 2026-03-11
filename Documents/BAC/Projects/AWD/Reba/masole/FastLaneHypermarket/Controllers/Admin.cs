using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace FastLaneHypermarket.Controllers
{
    public class AdminController : Controller
    {
        private readonly FastLaneContext _context;

        public AdminController(FastLaneContext context)
        {
            _context = context;
        }

        public async Task<IActionResult> Dashboard()
        {
            var customers = await _context.Customers
                .OrderByDescending(c => c.CustomerId)
                .ToListAsync();

            ViewBag.TotalCustomers = customers.Count;
            return View(customers);
        }
        public async Task<IActionResult> AdminDashboard()
        {
            // Get all staff
            var staff = await _context.Staff.ToListAsync();
            ViewBag.TotalStaff = staff.Count;

            // Get all customers (optional)
            var customers = await _context.Customers.ToListAsync();
            ViewBag.TotalCustomers = customers.Count;

            return View();
        }


        // 👨‍💼 Manage Staff
        public IActionResult Staff()
        {
            // TODO: Fetch all staff from database later
            return View();
        }

        // 📦 Manage Products
        public IActionResult Products()
        {
            // TODO: Fetch product list
            return View();
        }

        // 👥 Manage Customers
        public IActionResult Customers()
        {
            // TODO: Fetch customers from DB
            return View();
        }

        // 💰 View Sales
        public IActionResult Sales()
        {
            // TODO: Sales transactions view
            return View();
        }

        // 📊 Reports Page
        public IActionResult Reports()
        {
            return View();
        }

        // ⚙️ System Settings
        public IActionResult Settings()
        {
            return View();
        }
    }
}