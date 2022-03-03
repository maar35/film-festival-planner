using System.Text;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// A subsection is a section within a section.
    /// A film festival can group films thematically into sections.
    /// </summary>
    public class Subsection : ListStreamer
    {
        #region Poperties
        public int SubsectionId { get; }
        public int SectionId { get; }
        public string Name { get; }
        public string Description { get; }
        public string Url { get; }
        public Section Section { get; }
        #endregion

        #region Constructors
        public Subsection() { }

        public Subsection(string subsectionString)
        {
            // Assign the fields of the input string.
            string[] fields = subsectionString.Split(";");
            string subsectionId = fields[0];
            string sectionId = fields[1];
            Name = fields[2];
            Description = fields[3];
            Url = fields[4];

            // Assign properties that need calculating.
            SubsectionId = int.Parse(subsectionId);
            SectionId = int.Parse(sectionId);
            Section = ViewController.GetSection(SectionId);
        }
        #endregion

        #region Override Methods
        public override bool ListFileHasHeader()
        {
            return false;
        }

        public override bool ListFileIsMandatory()
        {
            return false;
        }

        public override string ToString()
        {
            var builder = new StringBuilder(Name);
            if (Description != string.Empty)
            {
                builder.AppendLine();
                builder.AppendLine();
                builder.Append(Description);
            }
            builder.AppendLine();
            builder.AppendLine();
            builder.Append($"{Name} is part of the {Section.Name} programme.");
            return builder.ToString();
        }
        #endregion
    }
}
