using System.ComponentModel.DataAnnotations;

namespace FastLaneHypermarket.Models
{
    public class Customer
    {
        [Key]
        public int CustomerId { get; set; }

        [Required]
        public string Firstname { get; set; } = string.Empty;

        [Required]
        public string Surname { get; set; } = string.Empty;

        public string? Gender { get; set; }

        public DateTime? DOB { get; set; }

        public string? Country { get; set; }

        public string? Role { get; set; }

        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;

        public string? CellNumber { get; set; }

        public string CustomerStatus { get; set; } = "Active";

        [Required]
        public string Password { get; set; } = string.Empty;

        // Computed property for full name
        public string FullName => $"{Firstname} {Surname}";

        // Computed property for age
        public int? Age
        {
            get
            {
                if (DOB.HasValue)
                {
                    var today = DateTime.Today;
                    var age = today.Year - DOB.Value.Year;
                    if (DOB.Value.Date > today.AddYears(-age)) age--;
                    return age;
                }
                return null;
            }
        }

       
    }
}