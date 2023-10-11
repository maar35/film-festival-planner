using System.Collections.Generic;
using System.Linq;

namespace PresentScreenings.TableView
{
    public class Theater : ListStreamer
    {
        #region Public Members
        public enum PriorityValue
        {
            NoGo,
            Low,
            High,
        }
        #endregion

        #region Properties
        public int TheaterId { get; }
        public City City { get; }
        public string Name { get; }
        public string Abbreviation { get; }
        public PriorityValue Priority { get; private set; }
        public static Dictionary<int, PriorityValue> PriorityByNumber { get; set; }
        #endregion

        #region Constructors
        // Static constructor.
        static Theater()
        {
            PriorityByNumber = new Dictionary<int, PriorityValue> { };
            PriorityByNumber.Add(0, PriorityValue.NoGo);
            PriorityByNumber.Add(1, PriorityValue.Low);
            PriorityByNumber.Add(2, PriorityValue.High);
        }

        // Constructor to read records from the interface file.
        public Theater(string theaterText)
        {
            // Assign the fields of the input string.
            string[] fields = theaterText.Split(';');
            string theaterId = fields[0];
            string cityIdString = fields[1];
            Name = fields[2];
            Abbreviation = fields[3];
            string priorityString = fields[4];

            // Assign properties that need calculating.
            TheaterId = int.Parse(theaterId);
            int cityId = int.Parse(cityIdString);
            City = ScreeningsPlan.Cities
                .Where(c => c.CityId == cityId)
                .First();
            Priority = PriorityByNumber[int.Parse(priorityString)];
        }

        // Empty constructor to facilitate ListStreamer method calls.
        public Theater() { }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override string ToString()
        {
            return $"{Name} {City}";
        }
        #endregion
    }
}
