using FastLaneHypermarket.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System;

namespace FastLaneHypermarket.Controllers
{
    public class AccountController : Controller
    {
        private readonly FastLaneContext _context;

        public AccountController(FastLaneContext context)
        {
            _context = context;
        }

        // ========================
        // 🧾 SIGNUP (GET)
        // ========================
        [HttpGet]
        public IActionResult Signup()
        {
            return View("~/Views/Shared/Signup.cshtml");
        }

        // ========================
        // 🧾 SIGNUP (POST)
        // ========================
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Signup(IFormCollection form)
        {
            // Extract form values with safe null handling
            string role = form["Role"].ToString() ?? "";
            string email = form["Email"].ToString() ?? "";
            string password = form["Password"].ToString() ?? "";
            string firstName = form["Firstname"].ToString() ?? "";
            string surname = form["Surname"].ToString() ?? "";
            string gender = form["Gender"].ToString() ?? "";
            string country = form["Country"].ToString() ?? "";
            string cellNumber = form["CellNumber"].ToString() ?? "";
            string position = form["Position"].ToString() ?? "";

            // Safe date parsing
            DateTime? dob = null;
            if (DateTime.TryParse(form["DOB"].ToString(), out DateTime parsedDob))
            {
                dob = parsedDob;
            }

            // Validate required fields
            if (string.IsNullOrEmpty(email) || string.IsNullOrEmpty(password) ||
                string.IsNullOrEmpty(firstName) || string.IsNullOrEmpty(surname))
            {
                TempData["Error"] = "Please fill all required fields.";
                return View();
            }

            // ✅ CUSTOMER SIGNUP
            if (role == "Customer")
            {
                var existingCustomer = await _context.Customers.FirstOrDefaultAsync(c => c.Email == email);
                if (existingCustomer != null)
                {
                    TempData["Error"] = "Email already registered as customer.";
                    return View();
                }

                var newCustomer = new Customer
                {
                    Firstname = firstName,
                    Surname = surname,
                    Gender = gender,
                    DOB = dob,
                    Country = country,
                    Email = email,
                    CellNumber = cellNumber,
                    Password = HashPassword(password),
                    CustomerStatus = "Active"
                };

                _context.Customers.Add(newCustomer);
                await _context.SaveChangesAsync();

                TempData["Success"] = "Customer account created successfully!";
                return RedirectToAction("Login");
            }

            // ✅ STAFF SIGNUP
            else if (role == "Staff")
            {
                var existingStaff = await _context.Staff.FirstOrDefaultAsync(s => s.Email == email);
                if (existingStaff != null)
                {
                    TempData["Error"] = "Email already registered as staff.";
                    return View();
                }

                var newStaff = new Staff
                {
                    Firstname = firstName,
                    Surname = surname,
                    Gender = gender,
                    DOB = dob,
                    Country = country,
                    Email = email,
                    CellNumber = cellNumber,
               
                    PasswordHash = HashPassword(password),
                    Role = "Staff",
                    StaffStatus = "Active"
                };

                _context.Staff.Add(newStaff);
                await _context.SaveChangesAsync();

                TempData["Success"] = "Staff account created successfully!";
                return RedirectToAction("Login");
            }

            TempData["Error"] = "Invalid role selected.";
            return View();
        }

        // ========================
        // 🔐 LOGIN (GET)
        // ========================
        [HttpGet]
        public IActionResult Login()
        {
            return View("~/Views/Shared/Login.cshtml");
        }

        // ========================
        // 🔐 LOGIN (POST)
        // ========================
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Login(string email, string password)
        {
            if (string.IsNullOrEmpty(email) || string.IsNullOrEmpty(password))
            {
                TempData["Error"] = "Please enter both email and password.";
                return View("~/Views/Shared/Login.cshtml");
            }

            // =========================================
            // 🔹 CHECK CUSTOMER LOGIN
            // =========================================
            var customer = await _context.Customers.FirstOrDefaultAsync(c => c.Email == email);

            if (customer != null && VerifyPassword(password, customer.Password))
            {
                // Save session data
                HttpContext.Session.SetInt32("CustomerId", customer.CustomerId);
                HttpContext.Session.SetString("UserRole", "Customer");

                string fullName = $"{customer.Firstname} {customer.Surname}";
                HttpContext.Session.SetString("UserName", fullName);

                string initials = $"{customer.Firstname[0]}{customer.Surname[0]}".ToUpper();
                HttpContext.Session.SetString("UserInitials", initials);

                TempData["Success"] = $"Welcome back, {customer.Firstname}!";

                return RedirectToAction("Index", "Home");
            }

            // =========================================
            // 🔹 CHECK STAFF LOGIN
            // =========================================
            var staff = await _context.Staff.FirstOrDefaultAsync(s => s.Email == email);

            if (staff != null && VerifyPassword(password, staff.PasswordHash))
            {
                // Save session
                HttpContext.Session.SetInt32("StaffId", staff.StaffId);
                HttpContext.Session.SetString("UserRole", staff.Role);

                string fullName = $"{staff.Firstname} {staff.Surname}";
                HttpContext.Session.SetString("UserName", fullName);

                string initials = $"{staff.Firstname[0]}{staff.Surname[0]}".ToUpper();
                HttpContext.Session.SetString("UserInitials", initials);

                if (staff.Role == "Admin")
                {
                    TempData["Success"] = $"Welcome Admin {staff.Firstname}!";
                    return RedirectToAction("Dashboard", "Admin");
                }

                TempData["Success"] = $"Welcome {staff.Firstname}!";
                return RedirectToAction("Dashboard", "Staff");
            }

            // =========================================
            // ❌ LOGIN FAILED
            // =========================================
            TempData["Error"] = "Invalid email or password.";
            return View("~/Views/Shared/Login.cshtml");
        }

        // ========================
        // 🔓 LOGOUT
        // ========================
       
        // ========================
        // 🚪 LOGOUT
        // ========================
        public IActionResult Logout()
        {
            HttpContext.Session.Clear();
            TempData["Success"] = "You have been logged out.";
            return RedirectToAction("Index", "Home");
        }

        // ========================
        // 🔑 PASSWORD HELPERS
        // ========================
        private string HashPassword(string password)
        {
            if (string.IsNullOrEmpty(password))
                return string.Empty;

            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(password));
                return BitConverter.ToString(bytes).Replace("-", "").ToLower();
            }
        }

        private bool VerifyPassword(string password, string hash)
        {
            if (string.IsNullOrEmpty(password) || string.IsNullOrEmpty(hash))
                return false;

            return HashPassword(password) == hash;
        }
    }
}