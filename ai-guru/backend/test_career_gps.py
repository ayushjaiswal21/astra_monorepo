"""Test script for Career GPS service"""
import sys
sys.path.append('.')

# Test importing the service
try:
    from .services import career_gps_service as career_gps
    print("✅ Successfully imported career_gps_service")
except Exception as e:
    print(f"❌ Failed to import career_gps_service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test calling the function
try:
    print("\n🧪 Testing analyze_career_preferences...")
    result = career_gps.analyze_career_preferences(
        interests=["programming", "design"],
        skills=["python", "creativity"],
        goal="build innovative products",
        motivation="make an impact",
        learning_style="hands-on",
        user_profile=None
    )
    print(f"\n✅ Got {len(result)} recommendations:")
    for i, career in enumerate(result, 1):
        print(f"  {i}. {career['name']} ({career['match']}%)")
except Exception as e:
    print(f"\n❌ Error calling analyze_career_preferences: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All tests passed!")
