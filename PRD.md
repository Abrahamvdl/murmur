I want a tool that plugs into my Wayland system where I can press a key combination on my keyboard and a small window pop up. (its a floating window). This window then starts recording my speech. Then when I am done speaking I press another button and the window goes away. However this window is just the visible part of the application, as the application runs in the background. The application transforms my speech into text. And when I close the window the text is pasted in the area where I had my cursor. 

I want the transcription to run on my AMD GPU. 
So first we will use 'faster_whisper' 
secondly after some googling, it looks like we should use ctranslate2-rocm from arlo-phoenix

We can use either c++ or python I don't care, having realtime transcription is what I want. I want to speak and see the text appear on the screen as I am talking, and then when I am done and happy, I can press that key combination that closes pop-up window and pastes the speech text into the area. 
