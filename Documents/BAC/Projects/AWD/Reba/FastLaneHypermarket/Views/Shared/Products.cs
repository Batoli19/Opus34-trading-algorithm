using Microsoft.AspNetCore.Mvc;

namespace FastLaneHypermarket.Views.Shared
{
    public class Products : Controller
    {
        public IActionResult Index()
        {
            return View();
        }
    }
}
