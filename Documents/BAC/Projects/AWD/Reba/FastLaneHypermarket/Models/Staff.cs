// Models/Staff.cs
using System;
using System.ComponentModel.DataAnnotations;

namespace FastLaneHypermarket.Models
{
    public class Staff
    {
        [Key]
        public int StaffId { get; set; }

        public string Firstname { get; set; }
        public string Surname { get; set; }
        public string Gender { get; set; }
        public DateTime? DOB { get; set; } // Change to nullable
        public string Country { get; set; }
        public string Email { get; set; }
        public string CellNumber { get; set; }
        public string StaffStatus { get; set; }
        public string PasswordHash { get; set; }
        public string Role { get; set; }
    }
}